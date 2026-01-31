import asyncio
from collections import deque
from typing import Deque

import websockets
from websockets import InvalidStatus
from websockets.exceptions import ConnectionClosedError
from camera.manager import CameraManager
from communication_protocol.message import Message
from communication_protocol.message_event import MessageEvent
from webapp.webapp import Webapp


class Router:
    """
    WebSocket router for bidirectional communication between server and local services.

    This class manages the WebSocket connection to the server and routes messages
    between the server and local components (camera manager, device broker).
    Provides automatic reconnection, message queuing, and error handling for
    reliable communication in distributed camera streaming system.
    """

    def __init__(self, uri: str, camera_manager: CameraManager, webapp: Webapp):
        """
        Initialize the router with server URI and camera manager.

        Args:
            uri (str): WebSocket server URI to connect to
            camera_manager (CameraManager): Camera manager instance for handling camera messages
        """

        self.uri = uri
        self.send_to_device = None
        self.message_queue: Deque[Message] = deque()
        self.camera_manager = camera_manager
        self.webapp = webapp

    async def start(self):
        """
        Start the router with automatic reconnection loop.

        This method maintains persistent connection to the server with automatic
        reconnection on failures. Handles connection errors gracefully and
        provides exponential backoff for connection attempts.
        """

        while True:
            try:
                async with websockets.connect(self.uri) as websocket:
                    print("Connected to server")
                    receive_from_server = asyncio.create_task(
                        self._receive_from_server(websocket)
                    )
                    send_to_server = asyncio.create_task(
                        self._send_to_server(websocket)
                    )
                    await asyncio.gather(receive_from_server, send_to_server)
            except (ConnectionClosedError, ConnectionRefusedError) as e:
                print("Connection to server closed or refused, retrying...")
                await asyncio.sleep(5)
                continue
            except InvalidStatus as e:
                print(f"WebSocket connection failed with invalid status: {e}")
                await asyncio.sleep(5)
                continue
            except Exception as e:
                print(f"Unexpected error in router connection: {e}")
                await asyncio.sleep(5)
                continue

    async def _receive_from_server(self, websocket: websockets.ClientConnection):
        """
        Handle incoming messages from the server.

        Routes messages based on device_id:
        - Camera messages: forwarded to camera manager
        - Other device messages: forwarded to device broker
        - Invalid messages: silently ignored with error logging

        Args:
            websocket: Active WebSocket connection to server
        """

        async for message in websocket:
            try:
                message = Message.model_validate_json(message)
                if message.message_event == MessageEvent.UPDATE_FIRMWARE:
                    asyncio.create_task(self.webapp.download_if_needed(message))
                elif message.device_id == "camera":
                    asyncio.create_task(self.camera_manager.on_message(message))
                else:
                    self.send_to_device(message)

            except Exception as e:
                print(f"Error processing incoming message: {e}")
                continue
            except KeyError as e:
                print(f"Missing required field in message: {e}")

    async def _send_to_server(self, websocket: websockets.ClientConnection):
        """
        Send queued messages to the server.

        Continuously processes the outgoing message queue, sending messages
        to the server via WebSocket.

        Args:
            websocket: Active WebSocket connection to server
        """
        while True:
            while len(self.message_queue) > 0:
                queued_message = self.message_queue.popleft()
                print(queued_message)
                await websocket.send(queued_message.model_dump_json())
                await asyncio.sleep(0.001)
            await asyncio.sleep(0.1)

    def send_to_server(self, message: Message):
        """
        Queue a message for sending to the server.

        Messages are queued and sent asynchronously by the _send_to_server task.
        This method is thread-safe and non-blocking.

        Args:
            message (Message): Message to send to server
        """

        self.message_queue.append(message)

    def bind_broker(self, broker):
        """
        Bind device broker for routing non-camera messages.

        Args:
            broker: Device broker instance with send_to_device method
        """

        self.send_to_device = broker.send_to_device
