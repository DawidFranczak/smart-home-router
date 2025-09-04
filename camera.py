import asyncio
import json
import uuid
from collections import deque
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCConfiguration, RTCIceServer, RTCIceCandidate
from aiortc.contrib.media import MediaPlayer

from communication_protocol.communication_protocol import DeviceMessage
from communication_protocol.message_event import MessageEvent
from communication_protocol.message_type import MessageType
from aiortc.sdp import SessionDescription

class Camera:
    def __init__(self,token:str, server_event, to_server_queue):
        self.pc = RTCPeerConnection(
            RTCConfiguration(
                iceServers=[RTCIceServer(urls="stun:stun.l.google.com:19302")]
            )
        )
        self.player = None
        self.server_event:asyncio.Event = server_event
        self.to_server_queue:deque = to_server_queue
        self.token = token

        @self.pc.on("icecandidate")
        def on_icecandidate(event):
            if event.candidate:
                response = DeviceMessage(
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
                self.server_event.set()

    async def handle_offer(self, payload:dict, message_id:str):
        rtsp = payload.get("rtsp")
        sdp = payload.get("offer", {}).get("sdp")
        offer_type = payload.get("offer", {}).get("type")

        offer = RTCSessionDescription(sdp=sdp, type=offer_type)
        await self.pc.setRemoteDescription(offer)

        if not self.player:
            try:
              self.add_player(rtsp)
            except Exception as e:
                self.get_wrong_rtsp_message(message_id)
                self.send_to_server(self.get_wrong_rtsp_message(message_id))
                await self.stop()
                return

        answer = await self.pc.createAnswer()
        await self.pc.setLocalDescription(answer)
        response = self.get_answer_message(message_id)
        self.send_to_server(response)

    # async def handle_candidate(self, candidate: dict):
    #     ice_candidate = RTCIceCandidate(
    #         sdpMid=candidate["sdpMid"],
    #         sdpMLineIndex=candidate["sdpMLineIndex"],
    #         candidate=candidate["candidate"],
    #     )
    #     await self.pc.addIceCandidate(ice_candidate)

    def message(self, message: dict):
        # print(f"Odebrano wiadomość dla kamery: {message}")

        if message["message_event"] == MessageEvent.CAMERA_OFFER.value:
            try:
                payload = message["payload"]
                asyncio.create_task(
                    self.handle_offer(payload, message["message_id"])
                )
            except Exception as e:
                print(e)
        elif message["message_event"] == MessageEvent.CAMERA_DISCONNECT.value:
            asyncio.create_task(self.stop())

        # elif message["message_event"] == MessageEvent.CAMERA_ICE:
        #     payload = json.loads(message["payload"])
        #     asyncio.create_task(self.handle_candidate(payload["candidate"]))

    async def stop(self):
        await self.pc.close()

    def get_answer_message(self, message_id:str) -> DeviceMessage:
        return DeviceMessage(
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
    def add_player(self, rtsp:str):
        self.player = MediaPlayer(rtsp, timeout=10)
        if self.player.video:
            self.pc.addTrack(self.player.video)
        if self.player.audio:
            self.pc.addTrack(self.player.audio)

    def send_to_server(self,message:DeviceMessage):
        self.to_server_queue.append(message.to_json())
        self.server_event.set()

    def get_wrong_rtsp_message(self, message_id:str) -> DeviceMessage:
        return DeviceMessage(
            message_type=MessageType.RESPONSE,
            message_event=MessageEvent.CAMERA_ERROR,
            device_id="camera",
            payload={
                "token": self.token,
                "error": "Wrong RTSP URL",
            },
            message_id=message_id,
        )