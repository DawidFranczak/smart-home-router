from uuid import uuid4

from communication_protocol.communication_protocol import DeviceMessage
from communication_protocol.message_event import MessageEvent
from communication_protocol.message_type import MessageType


def health_check_request(mac):
    return DeviceMessage(
        message_id=uuid4().hex,
        message_event=MessageEvent.HEALTH_CHECK,
        message_type=MessageType.REQUEST,
        device_id=mac,
        payload={},
    )


def device_disconnect_request(mac):
    return DeviceMessage(
        message_id=uuid4().hex,
        message_event=MessageEvent.DEVICE_DISCONNECT,
        message_type=MessageType.REQUEST,
        device_id=mac,
        payload={},
    )
