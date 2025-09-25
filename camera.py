import asyncio
import uuid
from collections import deque
from typing import Deque

from aiortc import (
    RTCPeerConnection,
    RTCSessionDescription,
    RTCConfiguration,
    RTCIceServer,
    RTCIceCandidate,
)
from aiortc.contrib.media import MediaPlayer, MediaRelay
from communication_protocol.communication_protocol import Message
from communication_protocol.message_event import MessageEvent
from communication_protocol.message_type import MessageType


class Camera:
    def __init__(self, token: str, to_server_queue, close_camera_connections):
        self.pc = RTCPeerConnection(
            RTCConfiguration(
                iceServers=[RTCIceServer(urls="stun:stun.l.google.com:19302")]
            )
        )
        self.player = None
        self.to_server_queue: Deque[Message] = to_server_queue
        self.token = token
        self.close_camera_connections = close_camera_connections

        @self.pc.on("icecandidate")
        def on_icecandidate(event):
            if event.candidate:
                response = Message(
                    message_type=MessageType.RESPONSE,
                    message_event=MessageEvent.CAMERA_ICE,
                    device_id="camera",
                    payload={
                        "token": self.token,
                        "candidate": {
                            "sdpMid": event.candidate.sdpMid,
                            "sdpMLineIndex": event.candidate.sdpMLineIndex,
                            "candidate": event.candidate.candidate,
                        },
                    },
                    message_id=uuid.uuid4().hex,
                )
                self.to_server_queue.append(response.to_json())

        @self.pc.on("connectionstatechange")
        async def on_connectionstatechange():
            if self.pc.connectionState in ["failed", "disconnected", "closed"]:
                await self.stop()
                self.close_camera_connections(self.token)

    async def handle_offer(self, payload: dict, message_id: str):
        rtsp = payload.get("rtsp")
        sdp = payload.get("offer", {}).get("sdp")
        offer_type = payload.get("offer", {}).get("type")
        try:
            offer = RTCSessionDescription(sdp=sdp, type=offer_type)
            await self.pc.setRemoteDescription(offer)
            if not self.player:
                await self.add_player(rtsp)
            answer = await self.pc.createAnswer()
            await self.pc.setLocalDescription(answer)
            response = self.get_answer_message(message_id)
            self.send_to_server(response)
        except Exception as e:
            error_message = self._get_error_message(e.args[0] if e.args else 0)
            self.send_to_server(
                self.get_camera_error_message(message_id, error_message)
            )
            await self.stop()

    # async def handle_candidate(self, candidate: dict):
    #     ice_candidate = RTCIceCandidate(
    #         sdpMid=candidate["sdpMid"],
    #         sdpMLineIndex=candidate["sdpMLineIndex"],
    #         candidate=candidate["candidate"],
    #     )
    #     await self.pc.addIceCandidate(ice_candidate)

    def message(self, message: Message):
        # print(f"Odebrano wiadomość dla kamery: {message}")
        if message.message_event == MessageEvent.CAMERA_OFFER.value:
            try:
                payload = message.payload
                if self.pc.connectionState in ["closed", "failed", "disconnected"]:
                    return
                asyncio.create_task(self.handle_offer(payload, message.message_id))
            except Exception as e:
                print(e)
        elif message.message_event == MessageEvent.CAMERA_DISCONNECT.value:
            asyncio.create_task(self.stop())

        # elif message.message_event == MessageEvent.CAMERA_ICE:
        #     payload = json.loads(message["payload"])
        #     asyncio.create_task(self.handle_candidate(payload["candidate"]))

    async def stop(self):
        await self.pc.close()

    def get_answer_message(self, message_id: str) -> Message:
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

    async def add_player(self, rtsp: str):
        print("start", rtsp)
        self.player = MediaPlayer(rtsp, timeout=10)
        print("stop", rtsp)

        if self.player.video:
            self.pc.addTrack(self.player.video)
        if self.player.audio:
            self.pc.addTrack(self.player.audio)

    def send_to_server(self, message: Message):
        self.to_server_queue.append(message)

    def get_camera_error_message(self, message_id: str, error: str) -> Message:
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

    def _get_error_message(self, errno: int) -> str:
        error_messages = {
            1: "Operation not permitted",
            2: "No such file or directory",
            5: "Input/output error",
            11: "Resource temporarily unavailable",
            22: "Invalid argument",
            110: "Connection timed out",
            1414092869: "Could not connect to camera",
        }
        return error_messages.get(errno, "Unknown error")
