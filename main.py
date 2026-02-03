import os
import asyncio
from pathlib import Path

from camera.manager import CameraManager
from mqtt import Mqtt
from router import Router
from webapp.webapp import Webapp
import logging
from logging.handlers import RotatingFileHandler

MQTT_PORT = os.getenv("MQTT_PORT", None)
MQTT_URL = os.getenv("MQTT_URL", None)
SERVER_URL = os.getenv("SERVER_URL", None)
ROUTER_MAC = os.getenv("ROUTER_MAC", None)
LOGGER_LEVEL = os.getenv("LOGGER_LEVEL", None)

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

def format_loggers():
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    logger = logging.getLogger()
    logger_level = LOGGER_LEVEL.upper() if LOGGER_LEVEL else "INFO"
    logger.setLevel(logger_level)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logger_level)

    file_handler = RotatingFileHandler(
        filename=LOG_DIR / "router.log",
        maxBytes=10*1024*1024,
        backupCount=5,
        encoding="utf-8"
    )

    file_handler.setFormatter(formatter)
    file_handler.setLevel(logger_level)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)


async def main():
    server_url = SERVER_URL+ROUTER_MAC+"/"
    camera_manager = CameraManager()
    mqtt = Mqtt(MQTT_URL, MQTT_PORT)
    webapp = Webapp(mqtt)
    router = Router(
        server_url, camera_manager, webapp
    )
    mqtt.bind_router(router)
    router.bind_broker(mqtt)
    mqtt.start()
    t1 = asyncio.create_task(webapp.start())
    t2 = asyncio.create_task(router.start())
    await asyncio.gather(t1, t2)


if __name__ == "__main__":
    if not MQTT_PORT:
        raise ValueError("MQTT_PORT is not set")
    if not MQTT_URL:
        raise ValueError("MQTT_URL is not set")
    if not SERVER_URL:
        raise ValueError("SERVER_URL is not set")
    if not ROUTER_MAC:
        raise ValueError("ROUTER_MAC is not set")
    try:
        MQTT_PORT = int(MQTT_PORT)
    except ValueError:
        raise ValueError("MQTT_PORT must be an integer")
    format_loggers()
    asyncio.run(main())
