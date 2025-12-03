from typing import Dict, Callable

from camera.connection import CameraConnection
from camera.session import CameraSession
from communication_protocol.communication_protocol import Message
from communication_protocol.message_event import MessageEvent
from communication_protocol.message_type import MessageType


class CameraManager:
    """
    Central manager for camera connections and WebRTC sessions.

    This class orchestrates the entire camera streaming system by managing:
    - RTSP camera connections (one per camera URL)
    - WebRTC sessions (one per client viewing a camera)
    - Message routing between clients and camera streams
    - Resource cleanup and lifecycle management

    Uses a shared connection model where multiple sessions can view the same
    camera through a single RTSP connection via MediaRelay.
    """

    def __init__(self):
        """
        Initialize the camera manager with empty connection and session pools.
        """
        self.connection: Dict[str, CameraConnection] = {}
        self.sessions: Dict[str, CameraSession] = {}
        self.send_to_server: Callable[[Message], None] | None = None

    def bind_router(self, router):
        """
        Bind the message router for server communication.

        Args:
            router: Router instance with send_to_server method
        """

        self.send_to_server = router.send_to_server

    async def on_message(self, message: Message):
        """
        Handle incoming camera-related messages from clients.

        Processes camera offer messages by:
        1. Creating or reusing camera connection for RTSP URL
        2. Creating new WebRTC session for the client
        3. Setting up media tracks and generating answer
        4. Handling errors and cleanup on failures

        Args:
            message (Message): Incoming message containing camera offer
        """
        token = message.payload["token"]
        if message.message_event == MessageEvent.CAMERA_OFFER.value:
            rtsp = message.payload["rtsp"]
            offer = message.payload["offer"]
            connection = await self._get_or_create_camera_connection(rtsp)
            session = CameraSession(token, rtsp, self.delete_session)
            self.sessions[token] = session
            try:
                tracks = await connection.get_tracks()
            except Exception as e:
                self.send_to_server(
                    self.get_camera_error_message(message.message_id, str(e), token)
                )
                await self.delete_session(token, rtsp)
                return
            message = await session.handle_offer(offer, tracks, message.message_id)
            self.send_to_server(message)
            connection.sessions.add(token)

    async def _get_or_create_camera_connection(self, rtsp: str) -> CameraConnection:
        """
        Get existing camera connection or create a new one for the RTSP URL.

        This method implements connection sharing - multiple sessions can use
        the same camera connection to reduce resource usage and improve performance.

        Args:
            rtsp (str): RTSP URL of the camera

        Returns:
            CameraConnection: Active connection to the camera
        """

        if rtsp in self.connection:
            return self.connection[rtsp]
        new_connection = CameraConnection(rtsp)
        self.connection[rtsp] = new_connection
        await new_connection.open()
        return new_connection

    async def delete_session(self, token: str, rtsp: str):
        """
        Clean up a session and its associated resources.

        This method:
        1. Stops and removes the WebRTC session
        2. Removes session reference from camera connection
        3. Closes camera connection if no more sessions are using it
        4. Performs garbage collection of unused resources

        Args:
            token (str): Session token to delete
            rtsp (str): RTSP URL associated with the session
        """

        if token in self.sessions:
            await self.sessions[token].stop()
            del self.sessions[token]
        if rtsp in self.connection:
            connection = self.connection[rtsp]
            connection.sessions.discard(token)
            if not connection.sessions:
                await connection.stop()
                del self.connection[rtsp]

    def get_camera_error_message(
        self, message_id: str, error: str, token: str
    ) -> Message:
        """
        Create standardized camera error message for client notification.

        Args:
            message_id (str): ID for message correlation
            error (str): Error description to send to client
            token (str): Session token experiencing the error

        Returns:
            Message: Formatted camera error message
        """

        return Message(
            message_type=MessageType.RESPONSE,
            message_event=MessageEvent.CAMERA_ERROR,
            device_id="camera",
            payload={
                "token": token,
                "error": error,
            },
            message_id=message_id,
        )
