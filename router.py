import json
import asyncio

import websockets
from collections import deque

from websockets import InvalidStatus
from websockets.exceptions import ConnectionClosedError

from communication_protocol.message import (
    device_disconnect_request,
)


class Router:
    def __init__(self):
        self.devices_message = {}  # mac:deque()
        self.devices_event = {}
        self.devices_connection = {}
        self.server_event = asyncio.Event()
        self.to_server_queue = deque()
        self.uri = "wss://dashing-cod-pretty.ngrok-free.app/ws/router/1234/"
        # self.uri = "ws://192.168.1.142:8000/ws/router/1234/"

    async def receive_from_server(self, websocket: websockets.ClientConnection):
        async for message in websocket:
            message_json = json.loads(message)
            data = json.loads(message_json)
            mac = data["device_id"]
            try:
                if mac in self.devices_message:
                    self.devices_message[mac].append(json.dumps(message_json))
                    self.devices_event[mac].set()
            except KeyError:
                print("KeyError",self.devices_message)

    async def send_to_server(self, websocket: websockets.ClientConnection):
        while True:
            if len(self.to_server_queue) == 0:
                await self.server_event.wait()
                self.server_event.clear()
                continue
            message = self.to_server_queue.popleft()
            await websocket.send(message)
            # print(f"Wysłano do serwera: {message}")

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
            except ConnectionClosedError or ConnectionRefusedError :
                print("Przerwano połączenie z serwerem. Próba połączenia za 5 sekund.")
                await asyncio.sleep(1)
                continue
            except InvalidStatus as e:
                print(e)
                await asyncio.sleep(5)
                continue
            except Exception as e:
                print(e)
                await asyncio.sleep(5)
                continue
    async def send_to_device(self, mac: str, writer: asyncio.StreamWriter):
        while self.devices_connection[mac]:
            if self.devices_message[mac]:
                message = self.devices_message[mac].popleft()
                writer.write(message.encode())
                await writer.drain()
                # print(f"Wysłano do {mac}: {message}")
            await asyncio.sleep(0.1)

    async def receive_from_device(self, mac: str, reader: asyncio.StreamReader,writer: asyncio.StreamWriter):
        while self.devices_connection[mac]:
            try:
                data = await asyncio.wait_for(reader.read(1024), timeout=2.0)
                if not data:
                    print("Brak danych")
                    self.devices_connection[mac] = False
                    return
                if data == b"P":
                    writer.write(b"P")
                    await writer.drain()
                    continue
                message = data.decode()
                idx = message.find("{")
                message = message[idx:]
                print(message)
                self.to_server_queue.append(message)
                self.server_event.set()
            except Exception as e:
                print(e)
                self.devices_connection[mac] = False
                return

    async def handle_device(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        print("Nowe połączenie z urządzeniem")
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
            print(e)
        except asyncio.CancelledError:
            print(f"Urządzenie {mac} rozłączone")
        finally:
            print(f"brak komunikacji z {mac}")
            if mac in self.devices_message:
                del self.devices_message[mac]
            if mac in self.devices_event:
                del self.devices_event[mac]
            if mac in self.devices_connection:
                del self.devices_connection[mac]
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

async def main(router: Router):
    await asyncio.gather(
        router.connect_to_server(), router.device_server()
    )


if __name__ == "__main__":
    router = Router()
    asyncio.run(main(router))
