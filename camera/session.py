from typing import Callable, Awaitable
from aiortc import (
    RTCPeerConnection,
    RTCSessionDescription,
    RTCConfiguration,
    RTCIceServer,
)
from communication_protocol.communication_protocol import Message
from communication_protocol.message_event import MessageEvent
from communication_protocol.message_type import MessageType


class CameraSession:
    """
    Manages a WebRTC session for streaming camera footage to a single client.

    This class handles the WebRTC peer connection lifecycle, including offer/answer
    exchange, track management, and connection state monitoring. Each session
    represents one client viewing a camera stream and automatically cleans up
    when the connection is closed or fails.
    """

    def __init__(
        self,
        token: str,
        rtsp: str,
        delete_callback: Callable[[str, str], Awaitable[None]],
    ):
        """
        Initialize a new camera session.

        Args:
            token (str): Unique identifier for this session
            rtsp (str): RTSP URL of the camera being streamed
            delete_callback: Async callback to clean up session when connection ends
        """

        self.pc = RTCPeerConnection(
            RTCConfiguration(
                iceServers=[
                    RTCIceServer(urls="stun:stun.l.google.com:19302"),
                ]
            )
        )
        self.rtsp = rtsp
        self.token = token
        self.delete_callback = delete_callback

        @self.pc.on("connectionstatechange")
        async def on_connectionstatechange():
            if self.pc.connectionState in ["failed", "disconnected", "closed"]:
                await self.stop()
                await self.delete_callback(self.token, self.rtsp)

    async def handle_offer(self, offer: dict, tracks, message_id: str) -> Message:
        """
        Process WebRTC offer from client and return answer message.

        Args:
            offer (dict): WebRTC offer containing SDP and type
            tracks: Media tracks to add to the peer connection
            message_id (str): ID for response message correlation

        Returns:
            Message: Camera answer message with SDP response
        """

        sdp = offer.get("sdp")
        offer_type = offer.get("type")
        offer = RTCSessionDescription(sdp=sdp, type=offer_type)
        await self.pc.setRemoteDescription(offer)
        for track in tracks:
            self.pc.addTrack(track)
        answer = await self.pc.createAnswer()
        await self.pc.setLocalDescription(answer)
        return self.get_answer_message(message_id)

    async def stop(self):
        """
        Stop the WebRTC session and close peer connection.

        This method properly closes the RTCPeerConnection to release
        resources and stop media transmission.
        """

        await self.pc.close()

    def get_answer_message(self, message_id: str) -> Message:
        """
        Create camera answer message with WebRTC SDP response.

        Args:
            message_id (str): ID for message correlation

        Returns:
            Message: Formatted camera answer message
        """

        return Message(
            message_type=MessageType.RESPONSE,
            message_event=MessageEvent.CAMERA_ANSWER,
            device_id="camera",
            payload={
                "token": self.token,
                "answer": {
                    "sdp": self.pc.localDescription.sdp,
                    "type": self.pc.localDescription.type,
                },
            },
            message_id=message_id,
        )

    def get_camera_error_message(self, message_id: str, error: str) -> Message:
        """
        Create camera error message for client notification.

        Args:
            message_id (str): ID for message correlation
            error (str): Error description

        Returns:
            Message: Formatted camera error message
        """

        return Message(
            message_type=MessageType.RESPONSE,
            message_event=MessageEvent.CAMERA_ERROR,
            device_id="camera",
            payload={
                "token": self.token,
                "error": error,
            },
            message_id=message_id,
        )
