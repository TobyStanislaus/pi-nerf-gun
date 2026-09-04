"""Central configuration.

Every value can be overridden with an environment variable so the broker
address and pins do not have to be edited in four different files.
"""
import os


def _env(name, default, cast=str):
    return cast(os.environ.get(name, default))


# MQTT
BROKER_IP = _env("NERF_BROKER_IP", "127.0.0.1")
BROKER_PORT = _env("NERF_BROKER_PORT", "1883", int)
KEEPALIVE = _env("NERF_KEEPALIVE", "30", int)
CLIENT_ID = _env("NERF_CLIENT_ID", "raspberry-pi-camera")
TOPIC_IMAGE = "image/stream"
TOPIC_RESPONSE = "response/decision"

# GPIO (BCM numbering)
SERVO_PIN = _env("NERF_SERVO_PIN", "18", int)
LED_PIN = _env("NERF_LED_PIN", "17", int)
RED_LED_PIN = _env("NERF_RED_LED_PIN", "15", int)

# Camera / stream
FRAME_WIDTH = _env("NERF_FRAME_WIDTH", "1920", int)
FRAME_HEIGHT = _env("NERF_FRAME_HEIGHT", "1080", int)
FRAME_SIZE = (FRAME_WIDTH, FRAME_HEIGHT)
FRAME_INTERVAL = _env("NERF_FRAME_INTERVAL", "0.1", float)
JPEG_QUALITY = _env("NERF_JPEG_QUALITY", "35", int)
# How long to wait for a frame before treating the camera as stalled.
CAPTURE_TIMEOUT = _env("NERF_CAPTURE_TIMEOUT", "5.0", float)

# Behaviour
COOLDOWN_TIME = _env("NERF_COOLDOWN", "1.0", float)
STATUS_TIMEOUT = _env("NERF_STATUS_TIMEOUT", "0.4", float)
