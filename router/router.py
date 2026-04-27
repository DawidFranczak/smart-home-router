import asyncio
from datetime import datetime, timedelta
import logging
from uuid import UUID

import websockets
from websockets import InvalidStatus
from websockets.exceptions import ConnectionClosedError
from camera.manager import CameraManager
from device_message.device_message import DeviceMessage
from device_message.enums import MessageCommand
from router.message import (
    ServerMessage,
    DeviceRouterMessage,
    RouterMessagePacket,
    CameraRouterMessage,
    AckRouterMessage,
)
from webapp.webapp import Webapp
from router.message import RouterMessage, RouterMessageType

logger = logging.getLogger(__name__)


class Router:
    def __init__(self, uri: str, camera_manager: CameraManager, webapp: Webapp):
        self.uri = uri
        self.send_to_device = None
        self.message_storage: dict[UUID, ServerMessage] = {}
        self.camera_manager = camera_manager
        self.webapp = webapp

    async def start(self):
        while True:
            try:
                async with websockets.connect(self.uri) as websocket:
                    logger.info("Connected to server")
                    receive_from_server = asyncio.create_task(
                        self._receive_from_server(websocket)
                    )
                    send_to_server = asyncio.create_task(
                        self._send_to_server(websocket)
                    )
                    await asyncio.gather(receive_from_server, send_to_server)
            except (ConnectionClosedError, ConnectionRefusedError) as e:
                logger.warning("Connection to server closed or refused, retrying...")
                await asyncio.sleep(5)
                continue
            except InvalidStatus as e:
                logger.warning(f"WebSocket connection failed with invalid status: {e}")
                await asyncio.sleep(5)
                continue

    async def _receive_from_server(self, websocket: websockets.ClientConnection):
        async for message in websocket:
            try:
                logger.info(f"Received message: {message}")
                message = RouterMessagePacket.model_validate_json(message).root
                if isinstance(message, DeviceRouterMessage):
                    if message.payload.command == MessageCommand.UPDATE_FIRMWARE:
                        asyncio.create_task(
                            self.webapp.download_if_needed(message.payload)
                        )
                    else:
                        self.send_to_device(message.payload)
                elif isinstance(message, CameraRouterMessage):
                    asyncio.create_task(self.camera_manager.on_message(message))
                elif isinstance(message, AckRouterMessage):
                    if message.message_id in self.message_storage:
                        del self.message_storage[message.message_id]

            except Exception as e:
                logger.error(f"Error processing incoming message: {e}")
                continue
            except KeyError as e:
                logger.error(f"Missing required field in message: {e}")

    async def _send_to_server(self, websocket: websockets.ClientConnection):
        while True:
            for message_id in list(self.message_storage.keys()):
                message = self.message_storage.get(message_id)
                if not message:
                    continue
                if datetime.now() - message.last_try > timedelta(seconds=5):
                    message.tries += 1
                    message.last_try = datetime.now()

                    print(f"To server: {message}")
                    await websocket.send(message.payload)
                    await asyncio.sleep(0.01)

                if message.tries > 50:
                    logger.error(
                        f"Message {message.payload} failed after 50 tries. Dropping."
                    )
                    del self.message_storage[message_id]
            await asyncio.sleep(0.1)

    def send_to_server(self, message: DeviceMessage):
        rm = DeviceRouterMessage(payload=message)
        self.message_storage[rm.message_id] = ServerMessage(
            payload=rm.model_dump_json()
        )

    def bind_broker(self, broker):
        self.send_to_device = broker.send_to_device
