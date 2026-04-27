import logging
from typing import Dict

from camera.message_payload import CameraRouterMessagePayload
from device_message.enums import CameraCommand
from subprocess import Popen, DEVNULL, TimeoutExpired
import asyncio

from router.message import CameraRouterMessage

logger = logging.getLogger(__name__)


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
        self.opened_stream: Dict[str, Popen] = {}
        self.lock = asyncio.Lock()

    async def on_message(self, message: CameraRouterMessage):
        async with self.lock:
            if message.command == CameraCommand.CAMERA_START:
                await self.start_stream(message.payload)

    async def start_stream(self, message: CameraRouterMessagePayload):
        if not message.rtsp:
            return
        camera_id = message.id
        rtsp = message.rtsp
        if rtsp in self.opened_stream:
            logger.info(f"pool for {rtsp} is {self.opened_stream[rtsp].poll()}")
            if self.opened_stream[rtsp].poll() is None:
                return
        logger.info(f"Starting stream for camera {rtsp}")
        cmd = [
            "ffmpeg",
            "-rtsp_transport",
            "tcp",
            "-i",
            rtsp,
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "64k",
            "-ar",
            "44100",
            "-map",
            "0:v",
            "-map",
            "0:a?",
            "-f",
            "rtsp",
            f"rtsp://172.155.0.10:8554/stream/{camera_id}",
        ]
        proc = Popen(cmd, stdout=DEVNULL, stderr=DEVNULL)
        self.opened_stream[rtsp] = proc

    async def stop_stream(self, message: CameraRouterMessage):
        camera_id = int(message.payload.id)
        if camera_id not in self.opened_stream:
            return
        self.opened_stream[camera_id][1] -= 1
        if self.opened_stream[camera_id][1] > 0:
            return
        self.opened_stream[camera_id][0].terminate()
        try:
            self.opened_stream[camera_id][0].wait(timeout=5)
        except TimeoutExpired:
            self.opened_stream[camera_id][0].kill()
        del self.opened_stream[camera_id]
