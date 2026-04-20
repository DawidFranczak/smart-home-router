from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, Field, TypeAdapter

from camera.message_payload import CameraRouterMessagePayload
from device_message.enums import CameraCommand
from device_message.device_message import DeviceMessage


class RouterMessageType(Enum):
    DEVICE = 0
    CAMERA = 1


class DeviceRouterMessage(BaseModel):
    target: Literal[0] = 0
    payload: DeviceMessage


class CameraRouterMessage(BaseModel):
    target: Literal[1] = 1
    command: CameraCommand
    payload: CameraRouterMessagePayload


RouterMessage = TypeAdapter(
    Annotated[DeviceRouterMessage | CameraRouterMessage, Field(discriminator="target")]
)
