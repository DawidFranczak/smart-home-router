import asyncio

from camera.manager import CameraManager
from mqtt import Mqtt
from router import Router
from webapp.webapp import Webapp


async def main():
    camera_manager = CameraManager()
    mqtt = Mqtt("localhost", 1883)
    webapp = Webapp(mqtt)
    router = Router(
        "wss://halpiszony.dpdns.org/ws/router/1234/", camera_manager, webapp
    )
    mqtt.bind_router(router)
    router.bind_broker(mqtt)
    mqtt.start()
    t1 = asyncio.create_task(webapp.start())
    t2 = asyncio.create_task(router.start())
    await asyncio.gather(t1, t2)


if __name__ == "__main__":
    asyncio.run(main())
