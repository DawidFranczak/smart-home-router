import asyncio
import websockets
from collections import deque

from pyexpat.errors import messages


class CommunicationModule:
    def __init__(self, device_mac):
        self.device_mac = device_mac
        self.uri = f"ws://192.168.1.142:8000/ws/device/{self.device_mac}/"
        self.to_server_queue = deque()
        self.from_server_queue = deque()

    async def receive_from_router(self, websocket: websockets.ServerConnection):
        async for message in websocket:
            print(f"Otrzymano od serwera: {message}")
            self.from_server_queue.append(message)
            await asyncio.sleep(1)

    async def send_to_router(self, websocket: websockets.ServerConnection):
        while True:
            if len(self.to_server_queue) == 0:
                message = await self.to_server_queue.popleft()
                await websocket.send(message)
            await asyncio.sleep(1)

    async def main(self):
        async with websockets.connect(self.uri) as websocket:
            send_to_router = asyncio.create_task(self.send_to_router(websocket))
            receive_from_router = asyncio.create_task(
                self.receive_from_router(websocket)
            )
            await asyncio.gather(receive_from_router, send_to_router)


if __name__ == "__main__":
    communication_module = CommunicationModule("1234")
    asyncio.run(communication_module.main())
