import re
from pydantic import BaseModel, field_validator
from .message_event import MessageEvent
from .message_type import MessageType


class Message(BaseModel):
    message_type: MessageType
    message_event: MessageEvent
    device_id: str
    message_id: str
    payload: dict | None

    @field_validator("device_id", mode="after")
    def validate_mac(cls, v):
        pattern = r"^([0-9a-fA-F]{2}[:-]){5}([0-9a-fA-F]){2}$"
        if not re.match(pattern, v) and v != "camera":
            raise ValueError("Invalid MAC address")
        return v

    @field_validator("payload")
    def validate_payload(cls, v):
        if v is None:
            return {}
        return v
