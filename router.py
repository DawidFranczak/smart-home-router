import asyncio
from collections import deque
from typing import Deque

import websockets
from websockets import InvalidStatus
from websockets.exceptions import ConnectionClosedError
from camera import Camera
from communication_protocol.message_event import MessageEvent
from communication_protocol.message import Message


class Router:
    def __init__(self, uri: str):
        self.cameras = {}
        self.uri = uri
        self.send_to_device = None
        self.message_queue: Deque[Message] = deque()

    async def start(self):
        while True:
            try:
                async with websockets.connect(self.uri) as websocket:
                    print("połączono z serwerem")
                    receive_from_server = asyncio.create_task(
                        self._receive_from_server(websocket)
                    )
                    send_to_server = asyncio.create_task(
                        self._send_to_server(websocket)
                    )
                    await asyncio.gather(receive_from_server, send_to_server)
            except (ConnectionClosedError, ConnectionRefusedError) as e:
                print(
                    "Połączenie z serwerem zamknięte lub odrzucone, ponawianie próby..."
                )
                await asyncio.sleep(5)
                continue
            except InvalidStatus as e:
                await asyncio.sleep(5)
                continue
            except Exception as e:
                await asyncio.sleep(5)
                continue

    async def _receive_from_server(self, websocket: websockets.ClientConnection):
        async for message in websocket:
            try:
                message = Message.model_validate_json(message)
                if message.device_id != "camera":
                    self.send_to_device(message)
                    continue
                token = message.payload.get("token", None)
                if not token:
                    continue
                camera_name = f"camera_{token}"
                camera = self.cameras.get(camera_name, None)
                if message.message_event == MessageEvent.CAMERA_OFFER.value:
                    if not camera_name in self.cameras:
                        camera = Camera(
                            token,
                            self.message_queue,
                            self.close_camera_connections,
                        )
                        self.cameras[camera_name] = camera
                if not camera:
                    continue
                camera.message(message)
            except Exception as e:
                print("Błąd podczas walidacji wiadomości:", e)
                continue
            except KeyError as e:
                pass

    async def _send_to_server(self, websocket: websockets.ClientConnection):
        while True:
            while len(self.message_queue) > 0:
                queued_message = self.message_queue.popleft()
                await websocket.send(queued_message.model_dump_json())
            await asyncio.sleep(0.1)

    def send_to_server(self, message: Message):
        self.message_queue.append(message)

    def bind_broker(self, broker):
        self.send_to_device = broker.send_to_device

    def close_camera_connections(self, token: str):
        name = f"camera_{token}"
        if name in self.cameras:
            del self.cameras[name]
