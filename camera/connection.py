import asyncio
from aiortc.contrib.media import MediaPlayer, MediaRelay


class CameraConnection:
    """
    Manages a single RTSP camera connection and provides media tracks to multiple sessions.

    This class handles the lifecycle of a camera connection, including opening/closing
    the RTSP stream and distributing media tracks to multiple WebRTC sessions.
    Uses MediaRelay to efficiently share the same media stream across sessions.
    """

    def __init__(self, rtsp: str):
        """
        Initialize a new camera connection.

        Args:
            rtsp (str): The RTSP URL of the camera stream
        """

        self.rtsp = rtsp
        self.player = None
        self.relay = MediaRelay()
        self._lock = asyncio.Lock()
        self._opened = asyncio.Event()
        self.sessions = set()

    async def get_tracks(self):
        """
        Get audio and video tracks from the camera stream.

        Returns:
            list: List of media tracks (audio/video) that can be added to WebRTC connections

        Raises:
            Exception: If camera is not available or connection failed
        """

        await self._opened.wait()
        if not self.player:
            raise Exception("Camera not available")
        tracks = []
        if self.player.audio:
            tracks.append(self.relay.subscribe(self.player.audio))
        if self.player.video:
            tracks.append(self.relay.subscribe(self.player.video))
        return tracks

    async def open(self):
        """
        Open the RTSP connection to the camera.

        This method is thread-safe and will only create one connection even if
        called multiple times concurrently. Uses an executor to avoid blocking
        the event loop during MediaPlayer creation.
        """

        async with self._lock:
            if self._opened.is_set() or self.player is not None:
                return
            try:
                loop = asyncio.get_event_loop()
                self.player = await loop.run_in_executor(
                    None, lambda: MediaPlayer(self.rtsp, timeout=10)
                )
                self._opened.set()
            except Exception as e:
                if self.player:
                    self.player = None
            finally:
                self._opened.set()

    async def stop(self):
        """
        Stop the camera connection and clean up resources.

        This method properly closes the MediaPlayer, clears all session references,
        and resets the connection state. Should be called when no more sessions
        are using this connection.
        """

        async with self._lock:
            self.player = None
            self._opened.clear()
            self.sessions.clear()
