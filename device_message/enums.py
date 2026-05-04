from typing import Union
from enum import StrEnum, Enum


class Scope(Enum):
    CPU = 1
    PERIPHERAL = 2


class MessageType(Enum):
    ACTION = 1
    EVENT = 2


class MessageDirection(Enum):
    INTENT = 1
    RESULT = 2


class ActionResult(Enum):
    ACCEPTED = 1
    REJECTED = 2


class DeviceStatuReport(Enum):
    ON = 1
    OFF = 2
    OPEN = 3
    CLOSED = 4


class CameraCommand(StrEnum):
    CAMERA_OFFER = "camera_offer"
    CAMERA_ANSWER = "camera_answer"
    CAMERA_DISCONNECT = "camera_disconnect"
    CAMERA_ERROR = "camera_error"
    CAMERA_START = "camera_start"
    CAMERA_STOP = "camera_stop"


class MessageEvent(StrEnum):
    # Basic events

    SET_SETTINGS = "set_settings"
    GET_SETTINGS = "get_settings"
    STATE_CHANGE = "state_change"
    UPDATE_FIRMWARE_ERROR = "update_firmware_error"
    UPDATE_CONFIG = "update_config"
    TURN_ON = "turn_on"
    TURN_OFF = "turn_off"

    # Measurement events
    ON_MEASURE_TEMPERATURE = "on_measure_temperature"
    ON_MEASURE_HUMIDITY = "on_measure_humidity"

    # Temperature events
    ON_TEMPERATURE_ABOVE = "on_temperature_above"
    ON_TEMPERATURE_BELOW = "on_temperature_below"

    # Humidity events
    ON_HUMIDITY_ABOVE = "on_humidity_above"
    ON_HUMIDITY_BELOW = "on_humidity_below"


class MessageAction(StrEnum):
    # RFID actions
    SET_VALUE = "set_value"
    SET_COLOR = "set_color"


class MessageCommand(StrEnum):
    # CPU events
    GET_CONNECTED_DEVICES = "get_connected_devices"
    DEVICE_CONNECT = "device_connect"
    DEVICE_DISCONNECT = "device_disconnect"

    # CPU action
    UPDATE_FIRMWARE = "update_firmware"
    UPDATE_FIRMWARE_ERROR = "update_firmware_error"
    UPDATE_PERIPHERAL = "update_peripheral"
    UPDATE_RULE = "update_rule"
    SYNC_START = "sync_start"
    SYNC_END = "sync_end"
    RESTART = "restart"

    # Peripheral events
    ON_TOGGLE = "on_toggle"
    ON_UPDATE_STATE = "on_update_state"
    ON_STATUS_REPORT = "on_status_report"
    ON_CLICK = "on_click"
    ON_HOLD = "on_hold"
    ON_ON = "on_on"
    ON_OFF = "on_off"
    ON_BLINK = "on_blink"
    ON_READ = "on_read"
    ON_READ_SUCCESS = "on_read_success"
    ON_READ_FAILURE = "on_read_failure"
    ON_SYNC_TIME = "on_sync_time"
    ON_MOTION = "on_motion"
    ON_MEASURE_TEMPERATURE = "on_measure_temperature"
    ON_MEASURE_HUMIDITY = "on_measure_humidity"

    # Peripheral action
    MOTION = "motion"
    TOGGLE = "toggle"
    UPDATE_STATE = "update_state"
    CLICK = "click"
    HOLD = "hold"
    ON = "on"
    OFF = "off"
    BLINK = "blink"
    ADD_TAG = "add_tag"
    ACCESS_GRANTED = "access_granted"
    ACCESS_DENIED = "access_denied"
    PLAY_SEQUENCE = "play_sequence"
