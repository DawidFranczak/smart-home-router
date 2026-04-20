import re
from typing import Any
from pydantic import BaseModel, field_validator

from device_message.enums import (
    MessageDirection,
    MessageCommand,
    MessageType,
    Scope,
)


class DeviceMessage(BaseModel):
    direction: MessageDirection
    command: MessageCommand
    type: MessageType
    scope: Scope
    device_id: str
    peripheral_id: int
    message_id: str
    payload: Any

    @field_validator("device_id", mode="after")
    def validate_mac(cls, value):
        pattern = r"^([0-9a-fA-F]{2}[:-]){5}([0-9a-fA-F]){2}$"
        if not re.match(pattern, value) and value != "camera":
            raise ValueError("Invalid MAC address")
        return value

    @field_validator("payload")
    def validate_payload(cls, v):
        if v is None:
            return {}
        return v
