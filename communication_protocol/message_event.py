from enum import Enum


class MessageEvent(Enum):
    DEVICE_CONNECT = "device_connect"
    DEVICE_DISCONNECT = "device_disconnect"
    CHECK_UID = "check_uid"
    ACTIVATE = "activate"
    DEACTIVATE = "deactivate"
    TURN_ON = "turn_on"
    TURN_OFF = "turn_off"
    HEALTH_CHECK = "health_check"
    GET_SETTINGS = "get_settings"
    SET_SETTINGS = "set_settings"
    READ_DATA = "read_data"
    WRITE_DATA = "write_data"
    ACCESS_GRANTED = "access_granted"
    ACCESS_DENIED = "access_denied"
    LAMP_TURNED_ON = "lamp_turned_on"
    LAMP_TURNED_OFF = "lamp_turned_off"
    SET_RGB = "set_rgb"
    SET_FLUO = "set_fluo"
    SET_LED = "set_led"
