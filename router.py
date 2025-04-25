import json
import asyncio
from datetime import datetime

import websockets
from collections import deque

from websockets import InvalidStatus
from websockets.exceptions import ConnectionClosedError

from communication_protocol.message import (
    device_disconnect_request,
)

def log(level: str, message: str) -> None:
    print(f"[{level}] {message}")
class Router:
    def __init__(self):
        self.devices_message = {}  # mac:deque()
        self.devices_event = {}
        self.devices_connection = {}
        self.server_event = asyncio.Event()
        self.to_server_queue = deque()
        # self.uri = "wss://dashing-cod-pretty.ngrok-free.app/ws/router/1234/"
        self.uri = "ws://192.168.1.143:8000/ws/router/1234/"
        log("INFO", "Inicjalizacja Routera")

    async def receive_from_server(self, websocket: websockets.ClientConnection):
        async for message in websocket:
            message_json = json.loads(message)
            mac = message_json["device_id"]
            try:
                if mac in self.devices_message:
                    self.devices_message[mac].append(message)
                    self.devices_event[mac].set()
                    log("INFO", f"Odebrano wiadomość dla {mac}: {message_json}")
                else:
                    log("WARNING", f"Nieznane urządzenie: {mac}")
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
            log("INFO", f"Wysłano do serwera: {message}")
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
                log("ERROR", f"Przerwano połączenie z serwerem: {e}. Próba za 5 sekund.")
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

    async def send_to_device(self, mac: str, writer: asyncio.StreamWriter):
        while self.devices_connection[mac]:
            if self.devices_message[mac]:
                message = self.devices_message[mac].popleft()
                writer.write(message.encode())
                await writer.drain()
                log("INFO", f"Wysłano do {mac}: {message}")
            await asyncio.sleep(0.1)

    async def receive_from_device(self, mac: str, reader: asyncio.StreamReader,writer: asyncio.StreamWriter):
        while self.devices_connection[mac]:
            try:
                data = await asyncio.wait_for(reader.read(1024), timeout=90.0)
                if not data:
                    log("ERROR", f"Brak danych od {mac}, rozłączam")
                    self.devices_connection[mac] = False
                    return
                if not data.strip():
                    print(data.strip())
                    continue
                message = data.decode()
                self.to_server_queue.append(message)
                self.server_event.set()
                log("INFO", f"Odebrano od {mac}: {message}")
            except asyncio.TimeoutError:
                log("INFO", f"Timeout od {mac}, kontynuuję...")
                self.devices_connection[mac] = False
                continue
            except Exception as e:
                log("ERROR", f"Błąd od {mac}: {e}")
                self.devices_connection[mac] = False
                return

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
        except UnicodeDecodeError:
            log("ERROR", f"Błąd dekodowania danych początkowych: {e}")
            return
        log("INFO", f"Podłączono urządzenie: {mac}")

        self.devices_message[mac] = deque()
        self.devices_event[mac] = asyncio.Event()
        self.devices_connection[mac] = True
        self.to_server_queue.append(initial_data)
        self.server_event.set()
        send_task = asyncio.create_task(self.send_to_device(mac, writer))
        receive_task = asyncio.create_task(self.receive_from_device(mac, reader,writer))
        try:
            await asyncio.gather(send_task, receive_task, return_exceptions=True)
        except Exception as e:
            log("ERROR", f"Błąd w obsłudze urządzenia {mac}: {e}")
        except asyncio.CancelledError:
            print(f"Urządzenie {mac} rozłączone")
        finally:
            log("INFO", f"Rozłączono urządzenie {mac}")
            # if mac in self.devices_message:
            #     del self.devices_message[mac]
            # if mac in self.devices_event:
            #     del self.devices_event[mac]
            # if mac in self.devices_connection:
            #     del self.devices_connection[mac]
            self.to_server_queue.append(device_disconnect_request(mac).to_json())
            self.server_event.set()
            try:
                writer.close()
                await writer.wait_closed()
            except Exception as e:
                log("ERROR", f"Błąd zamykania połączenia {mac}: {e}")

    async def device_server(self):
        server = await asyncio.start_server(self.handle_device, "0.0.0.0", 8080)
        log("INFO", f"Serwer TCP dla urządzeń uruchomiony na porcie 8080")
        async with server:
            await server.serve_forever()

async def main(router: Router):
    await asyncio.gather(
        router.connect_to_server(), router.device_server()
    )


if __name__ == "__main__":
    router = Router()
    asyncio.run(main(router))
