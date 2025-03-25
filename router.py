import json
import asyncio
import websockets
from collections import deque
from websockets.exceptions import ConnectionClosedError

from communication_protocol.communication_protocol import DeviceMessage
from communication_protocol.message import (
    health_check_request,
    device_disconnect_request,
)
from communication_protocol.message_event import MessageEvent
from communication_protocol.message_type import MessageType


class Router:
    def __init__(self):
        self.devices_message = {}  # mac:deque()
        self.devices_event = {}
        self.devices_connection = {}
        self.server_event = asyncio.Event()
        self.to_server_queue = deque()
        self.uri = "ws://192.168.1.143:8000/ws/router/1234/"

    async def receive_from_server(self, websocket: websockets.ClientConnection):
        async for message in websocket:
            message_json = json.loads(message)
            data = json.loads(message_json)
            mac = data["device_id"]
            try:
                self.devices_message[mac].append(json.dumps(message_json))
                self.devices_event[mac].set()
            except KeyError:
                print(self.devices_message)

    async def send_to_server(self, websocket: websockets.ClientConnection):
        while True:
            if len(self.to_server_queue) == 0:
                await self.server_event.wait()
                self.server_event.clear()
                continue
            message = self.to_server_queue.popleft()
            await websocket.send(message)
            print(f"Wysłano do serwera: {message}")

    async def connect_to_server(self):
        while True:
            try:
                async with websockets.connect(self.uri) as websocket:
                    print("Połączono z serwerem")
                    send_to_server = asyncio.create_task(self.send_to_server(websocket))
                    receive_from_server = asyncio.create_task(
                        self.receive_from_server(websocket)
                    )
                    await asyncio.gather(send_to_server, receive_from_server)
            except ConnectionClosedError:
                print("Przerwano połączenie z serwerem. Próba połączenia za 5 sekund.")
                await asyncio.sleep(1)
                continue
            except ConnectionRefusedError:
                print("Odrzucono połączenie z serwerem. Próba połączenia za 5 sekund.")
                await asyncio.sleep(1)
                continue

    async def send_to_device(self, mac: str, writer: asyncio.StreamWriter):
        while not self.devices_connection[mac]["writer"].is_closing():
            if self.devices_message[mac]:
                message = self.devices_message[mac].popleft()
                writer.write(message.encode())
                await writer.drain()
                print(f"Wysłano do {mac}: {message}")
            await asyncio.sleep(0.1)

    async def receive_from_device(self, mac: str, reader: asyncio.StreamReader):
        while not self.devices_connection[mac]["writer"].is_closing():
            data = await reader.read(1024)  # Odczyt danych od klienta
            if not data:
                return
            message = data.decode()
            self.to_server_queue.append(message)
            self.server_event.set()

    async def handle_device(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        try:
            initial_data = await asyncio.wait_for(reader.read(1024), timeout=5.0)
            if not initial_data:
                writer.close()
                await writer.wait_closed()
                return
        except asyncio.TimeoutError:
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
            return
        print(f"Podłączono urządzenie: {mac}")

        if mac in self.devices_connection:
            await self._close_old_connection(mac)

        self.devices_message[mac] = deque()
        self.devices_event[mac] = asyncio.Event()
        self.to_server_queue.append(initial_data)
        self.server_event.set()
        send_task = asyncio.create_task(self.send_to_device(mac, writer))
        receive_task = asyncio.create_task(self.receive_from_device(mac, reader))
        self.devices_connection[mac] = {
            "writer": writer,
            "send_to_device": send_task,
            "receive_from_device": receive_task,
        }
        try:
            await asyncio.gather(send_task, receive_task, return_exceptions=True)
        except Exception as e:
            print(e)
        except asyncio.CancelledError:
            print(f"Urządzenie {mac} rozłączone")
        finally:
            # Usuń urządzenie po rozłączeniu
            print(f"brak komunikacji z {mac}")
            if self.devices_connection[mac]["writer"].is_closing():
                if mac in self.devices_message:
                    del self.devices_message[mac]
                if mac in self.devices_event:
                    del self.devices_event[mac]
                self.to_server_queue.append(device_disconnect_request(mac).to_json())
            self.server_event.set()
            try:
                writer.close()
                await writer.wait_closed()
            except Exception as e:
                print("Zamykanie", e)

    async def device_server(self):
        server = await asyncio.start_server(self.handle_device, "0.0.0.0", 8080)
        print(f"Serwer TCP dla urządzeń uruchomiony na porcie 8080")
        async with server:
            await server.serve_forever()

    async def check_device(self):
        while True:
            for mac in self.devices_connection:
                message = health_check_request(mac)
                if mac in self.devices_message:
                    self.devices_message[mac].append(json.dumps(message.to_json()))
                if mac in self.devices_event:
                    self.devices_event[mac].set()
            await asyncio.sleep(60)

    async def _close_old_connection(self, mac: str):
        self.devices_connection[mac]["writer"].close()
        await self.devices_connection[mac]["writer"].wait_closed()
        self.devices_connection[mac]["send_to_device"].cancel()
        self.devices_connection[mac]["receive_from_device"].cancel()
        try:
            await asyncio.gather(
                self.devices_connection[mac]["send_to_device"],
                self.devices_connection[mac]["receive_from_device"],
                return_exceptions=True,
            )
        except asyncio.CancelledError:
            pass

        del self.devices_connection[mac]
        if mac in self.devices_message:
            del self.devices_message[mac]
        if mac in self.devices_event:
            del self.devices_event[mac]


async def main(router: Router):
    await asyncio.gather(
        router.connect_to_server(), router.device_server(), router.check_device()
    )


if __name__ == "__main__":
    router = Router()
    asyncio.run(main(router))
