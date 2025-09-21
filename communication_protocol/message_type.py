from enum import Enum


class MessageType(str, Enum):
    REQUEST = "request"
    RESPONSE = "response"
