import asyncio

from mqtt import Mqtt
from router import Router


if __name__ == "__main__":
    mqtt = Mqtt("192.168.1.142", 1883)
    router = Router("ws://192.168.1.142:80/ws/router/1234/")

    mqtt.bind_router(router)
    router.bind_broker(mqtt)

    mqtt.start()
    asyncio.run(router.start())
