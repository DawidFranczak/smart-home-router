from uuid import uuid4

from communication_protocol.communication_protocol import Message
from communication_protocol.message_event import MessageEvent
from communication_protocol.message_type import MessageType


def health_check_request(mac):
    return Message(
        message_type=MessageType.REQUEST,
        message_event=MessageEvent.HEALTH_CHECK,
        message_id=uuid4().hex,
        device_id=mac,
        payload={},
    )


def device_disconnect_request(mac):
    return Message(
        message_type=MessageType.REQUEST,
        message_event=MessageEvent.DEVICE_DISCONNECT,
        message_id=uuid4().hex,
        device_id=mac,
        payload={},
    )
