import time
from collections import deque
from typing import Deque

import paho.mqtt.client as mqtt
from paho.mqtt.properties import PacketTypes, Properties
from communication_protocol.communication_protocol import Message
from communication_protocol.message_event import MessageEvent


class Mqtt:
    def __init__(self, ip: str, port: int, keepalive: int = 60):
        self.ip = ip
        self.port = port
        self.keepalive = keepalive
        self.send_to_server = None
        self.message_queue: Deque[Message] = deque()

        self.client = mqtt.Client(
            client_id="Hub",
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            protocol=mqtt.MQTTv5,
            reconnect_on_failure=True,
        )

        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        self.client.on_connect_fail = self.on_connect_fail

    def on_connect(self, client, userdata, flags, reasonCode, properties):
        self.client.subscribe("hub", qos=1)
        print("Connected to MQTT broker")
        while len(self.message_queue) > 0:
            self.send_to_server(self.message_queue.popleft())

    def on_disconnect(self, client, userdata, reasonCode, properties, *args):
        self._connect()

    def on_connect_fail(self, client, userdata):
        time.sleep(5)
        self._connect()

    def on_message(self, client, userdata, message):
        if not message.payload:
            return
        try:
            self.send_to_server(Message.model_validate_json(message.payload.decode()))
        except Exception as e:
            print("Error processing message:", e)

    def send_to_device(self, message: Message):

        if not self.client.is_connected():
            self.message_queue.append(message)
            return
        if message.message_event == MessageEvent.GET_CONNECTED_DEVICES.value:
            self.client.publish(f"device/broadcast/", message.model_dump_json(), qos=1)
            return
        self.client.publish(
            f"device/{message.device_id}/", message.model_dump_json(), qos=1
        )

    def bind_router(self, router):
        self.send_to_server = router.send_to_server

    def start(self):
        self._connect()
        self.client.loop_start()

    def _connect(self):
        try:
            props = Properties(PacketTypes.CONNECT)
            props.SessionExpiryInterval = 3600
            self.client.connect(
                self.ip, self.port, self.keepalive, clean_start=False, properties=props
            )
        except ConnectionRefusedError:
            print("Connection refused. Retrying in 5 seconds...")
