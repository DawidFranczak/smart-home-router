from enum import IntEnum
from typing import Annotated, Type, Union, Literal
from uuid import uuid4, UUID

from camera.message_payload import CameraRouterMessagePayload
from device_message.enums import CameraCommand
from device_message.device_message import DeviceMessage

from datetime import datetime, timedelta

from pydantic import BaseModel, Field, RootModel


def get_message_id() -> str:
    return uuid4().hex


def get_start_time() -> datetime:
    return datetime.now() - timedelta(minutes=10)


class RouterMessageType(IntEnum):
    DEVICE = 0
    CAMERA = 1
    ACK = 2


def generate_random_id():
    return uuid4()


class RouterMessage(BaseModel):
    target: RouterMessageType
    message_id: UUID = Field(default_factory=generate_random_id)


class DeviceRouterMessage(RouterMessage):
    target: Literal[RouterMessageType.DEVICE] = RouterMessageType.DEVICE
    payload: DeviceMessage


class CameraRouterMessage(RouterMessage):
    target: Literal[RouterMessageType.CAMERA] = RouterMessageType.CAMERA
    command: CameraCommand
    payload: CameraRouterMessagePayload


class AckRouterMessage(RouterMessage):
    target: Literal[RouterMessageType.ACK] = RouterMessageType.ACK


class RouterMessagePacket(RootModel):
    root: Annotated[
        Union[DeviceRouterMessage, CameraRouterMessage, AckRouterMessage],
        Field(discriminator="target"),
    ]


class ServerMessage(BaseModel):
    payload: str
    last_try: datetime = Field(default_factory=get_start_time)
    tries: int = Field(default=0)
