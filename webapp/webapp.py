import aiohttp
from aiohttp import web
import os
import socket
from communication_protocol.communication_protocol import Message
from mqtt import Mqtt


def get_local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


class Webapp:
    def __init__(self, mqtt: Mqtt):
        self.FIRMWARE_DIR = os.path.join(os.getcwd(), "firmware")
        os.makedirs(self.FIRMWARE_DIR, exist_ok=True)
        self.address = None
        self.mqtt = mqtt

    async def start(self, port=8452):
        app = web.Application()
        app.router.add_get("/ota", self.serve_firmware)
        runner = web.AppRunner(app)
        await runner.setup()
        local_ip = get_local_ip()
        site = web.TCPSite(runner, local_ip, port)
        self.address = f"http://{local_ip}:{port}/ota"
        await site.start()

    async def download_if_needed(self, message: Message) -> None:
        device_fun = message.payload.get("to_device")
        version = message.payload.get("version")
        url = message.payload.get("url")
        if not device_fun or not version or not url:
            return

        filename = f"{device_fun}_{version}.bin"
        filepath = os.path.join(self.FIRMWARE_DIR, filename)
        if not os.path.exists(filepath):
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.read()
                        with open(filepath, "wb") as f:
                            f.write(data)
                    else:
                        raise web.HTTPNotFound(text="Firmware not available")
        message.payload["url"] = f"{self.address}?name={filename}"
        self.mqtt.send_to_device(message)

    async def serve_firmware(self, request):
        name = request.query.get("name")
        if not name:
            raise web.HTTPBadRequest()
        return web.FileResponse(
            os.path.join(self.FIRMWARE_DIR, name),
            headers={
                "Content-Type": "application/octet-stream",
                "Content-Disposition": f'attachment; filename="firmware.bin"',
            },
        )
