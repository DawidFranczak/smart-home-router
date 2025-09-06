import json
import asyncio
from os import access
from uuid import uuid4, UUID
import websockets
from collections import deque

from websockets import InvalidStatus
from websockets.exceptions import ConnectionClosedError

from camera import Camera
from communication_protocol.message import (
    device_disconnect_request,
)
from communication_protocol.message_event import MessageEvent


def log(level: str, message: str) -> None:
    print(f"[{level}] {message}")


class Router:
    def __init__(self):
        self.connection_devices = {}
        self.cameras = {}
        self.server_event = asyncio.Event()
        self.to_server_queue = deque()
        # self.uri = "wss://dashing-cod-pretty.ngrok-free.app/ws/router/1234/"
        self.uri = "ws://localhost:80/ws/router/1234/"
        log("INFO", "Inicjalizacja Routera")

    async def receive_from_server(self, websocket: websockets.ClientConnection):
        async for message in websocket:
            message = message.replace("'", '"')
            message_json = json.loads(message)
            mac = message_json.get("device_id")
            try:
                if not mac:
                    log("WARNING", f"Nieznane urządzenie: {mac}")
                    continue
                if mac in self.connection_devices:
                    self.connection_devices[mac]["queue"].append(message)
                    continue
                token = message_json.get("payload").get("token")
                if not token:
                    continue
                camera_name = f"camera_{token}"
                camera = self.cameras.get(camera_name, None)
                message_event = message_json.get("message_event", None)
                if not message_event:
                    continue
                if message_event == MessageEvent.CAMERA_OFFER.value:
                    if not camera_name in self.cameras:
                        camera = Camera(token,self.server_event,self.to_server_queue)
                        self.cameras[camera_name] = camera
                elif message_event == MessageEvent.CAMERA_DISCONNECT.value:
                    if camera_name in self.cameras:
                        del self.cameras[camera_name]
                if not camera:
                    continue
                camera.message(message_json)
            except KeyError as e:
                log("ERROR", f"KeyError: {e}, devices_message: {self.devices_message}")

    async def send_to_server(self, websocket: websockets.ClientConnection):
        while True:
            if len(self.to_server_queue) == 0:
                await self.server_event.wait()
                self.server_event.clear()
                continue
            message = self.to_server_queue.popleft()
            await websocket.send(message)
            # log("INFO", f"Wysłano do serwera: {message}")
            # print(f"Wysłano do serwera: {message}")

    async def connect_to_server(self):
        while True:
            try:
                async with websockets.connect(self.uri) as websocket:
                    log("INFO", "Połączono z serwerem")
                    send_to_server = asyncio.create_task(self.send_to_server(websocket))
                    receive_from_server = asyncio.create_task(
                        self.receive_from_server(websocket)
                    )
                    await asyncio.gather(send_to_server, receive_from_server)
            except (ConnectionClosedError, ConnectionRefusedError) as e:
                log(
                    "ERROR", f"Przerwano połączenie z serwerem: {e}. Próba za 5 sekund."
                )
                await asyncio.sleep(5)
                continue
            except InvalidStatus as e:
                log("ERROR", f"InvalidStatus: {e}")
                await asyncio.sleep(5)
                continue
            except Exception as e:
                log("ERROR", f"Błąd: {e}")
                await asyncio.sleep(5)
                continue

    async def send_to_device(self, mac: str, token: UUID, writer: asyncio.StreamWriter):
        while self.connection_devices[mac].get("token", None) == token:
            if self.connection_devices[mac]["queue"]:
                message = self.connection_devices[mac]["queue"].popleft()
                writer.write(message.encode())
                await writer.drain()
                # log("INFO", f"Wysłano do {mac}: {message}")
            await asyncio.sleep(0.1)

    async def receive_from_device(
        self, mac: str, token: UUID, reader: asyncio.StreamReader
    ):
        while self.connection_devices[mac].get("token", None) == token:
            data = await asyncio.wait_for(reader.read(1024), timeout=90.0)
            if not data:
                log("ERROR", f"Brak danych od {mac}, rozłączam")
                raise ConnectionResetError()
            if not data.strip():
                continue
            message = data.decode()
            self.to_server_queue.append(message)
            self.server_event.set()

    async def handle_device(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        log("INFO", "Nowe połączenie z urządzeniem")
        try:
            initial_data = await asyncio.wait_for(reader.read(1024), timeout=5.0)
            if not initial_data:
                log("ERROR", "Brak danych początkowych, zamykam połączenie")
                writer.close()
                await writer.wait_closed()
                return
        except asyncio.TimeoutError:
            log("ERROR", "Timeout danych początkowych, zamykam połączenie")
            writer.close()
            await writer.wait_closed()
            return
        try:
            initial_data = initial_data.decode("utf-8")
            data = json.loads(initial_data)
            ip, port = writer.get_extra_info("peername")
            mac = data["device_id"]
            data["payload"]["ip"] = ip
            data["payload"]["port"] = port
            initial_data = json.dumps(data)
        except UnicodeDecodeError as e:
            log("ERROR", f"Błąd dekodowania danych początkowych: {e}")
            return

        connection_token = uuid4()
        log("INFO", f"Podłączono urządzenie: {mac,connection_token}")
        self.connection_devices[mac] = {
            "token": connection_token,
            "queue": deque(),
        }
        self.to_server_queue.append(initial_data)
        self.server_event.set()
        send_task = asyncio.create_task(
            self.send_to_device(mac, connection_token, writer)
        )
        receive_task = asyncio.create_task(
            self.receive_from_device(mac, connection_token, reader)
        )
        try:
            await asyncio.gather(send_task, receive_task)
        except asyncio.TimeoutError:
            log("WARNING", f"Timeout połączenia z urządzeniem {mac, connection_token}")
        except ConnectionResetError:
            log(
                "ERROR",
                f"Połączenie z urządzeniem {mac, connection_token} zostało zresetowane",
            )
        except Exception as e:
            log("ERROR", f"Błąd w obsłudze urządzenia {mac, connection_token}: {e}")
        finally:
            log("INFO", f"Rozłączono urządzenie {mac, connection_token}")
            if mac in self.connection_devices:
                if self.connection_devices[mac]["token"] == connection_token:
                    del self.connection_devices[mac]
                    self.to_server_queue.append(
                        device_disconnect_request(mac).to_json()
                    )
                    self.server_event.set()

    async def device_server(self):
        server = await asyncio.start_server(self.handle_device, "0.0.0.0", 8080)
        log("INFO", f"Serwer TCP dla urządzeń uruchomiony na porcie 8080")
        async with server:
            await server.serve_forever()


async def main(router: Router):
    await asyncio.gather(router.connect_to_server(), router.device_server())


if __name__ == "__main__":
    router = Router()
    asyncio.run(main(router))
