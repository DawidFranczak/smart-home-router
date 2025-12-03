from enum import Enum


class MessageEvent(str, Enum):
    # Basic events
    GET_CONNECTED_DEVICES = "get_connected_devices"
    DEVICE_CONNECT = "device_connect"
    DEVICE_DISCONNECT = "device_disconnect"
    HEALTH_CHECK = "health_check"
    SET_SETTINGS = "set_settings"
    GET_SETTINGS = "get_settings"
    STATE_CHANGE = "state_change"
    UPDATE_FIRMWARE = "update_firmware"
    UPDATE_FIRMWARE_ERROR = "update_firmware_error"

    # Button events
    ON_CLICK = "on_click"
    ON_HOLD = "on_hold"
    ON_TOGGLE = "on_toggle"

    # Light events
    ON = "on"
    OFF = "off"
    BLINK = "blink"
    TOGGLE = "toggle"

    # RFID events
    ADD_TAG = "add_tag"
    ON_READ = "on_read"
    ON_READ_SUCCESS = "on_read_success"
    ON_READ_FAILURE = "on_read_failure"
    ACCESS_GRANTED = "access_granted"
    ACCESS_DENIED = "access_denied"

    # Camera events
    CAMERA_OFFER = "camera_offer"
    CAMERA_ANSWER = "camera_answer"
    CAMERA_DISCONNECT = "camera_disconnect"
    CAMERA_ERROR = "camera_error"

    # Sensor events
    MEASURE_TEMPERATURE = "measure_temperature"
    MEASURE_HUMIDITY = "measure_humidity"

    # Measurement events
    ON_MEASUREMENT_TEMP_HUM = "on_measurement_temp_hum"

    # Temperature events
    ON_TEMPERATURE_ABOVE = "on_temperature_above"
    ON_TEMPERATURE_BELOW = "on_temperature_below"

    # Humidity events
    ON_HUMIDITY_ABOVE = "on_humidity_above"
    ON_HUMIDITY_BELOW = "on_humidity_below"
