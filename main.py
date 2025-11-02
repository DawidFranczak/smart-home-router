import asyncio

from camera.manager import CameraManager
from mqtt import Mqtt
from router import Router


if __name__ == "__main__":
    camera_manager = CameraManager()
    # router = Router("ws://192.168.1.142:80/ws/router/1234/", camera_manager)
    mqtt = Mqtt("localhost", 1883)
    router = Router(
        "wss://dashing-cod-pretty.ngrok-free.app/ws/router/1234/", camera_manager
    )

    mqtt.bind_router(router)
    router.bind_broker(mqtt)
    camera_manager.bind_router(router)

    mqtt.start()
    asyncio.run(router.start())
