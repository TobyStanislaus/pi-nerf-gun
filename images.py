"""Encode a camera frame and publish it on an already-connected MQTT client."""
import base64

import cv2
import paho.mqtt.client as mqtt

from config import JPEG_QUALITY, TOPIC_IMAGE


def encode_frame(image, quality=JPEG_QUALITY):
    ok, buffer = cv2.imencode(".jpeg", image, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        raise RuntimeError("cv2.imencode failed")
    return base64.b64encode(buffer).decode("utf-8")


def send_image(client, image, topic=TOPIC_IMAGE, quality=JPEG_QUALITY):
    """Publish one frame on the shared client. Returns True if it was queued.

    The client is passed in on purpose: opening a fresh connection per frame
    exhausts sockets and makes the broker evict the other client using the same
    client id.
    """
    info = client.publish(topic, encode_frame(image, quality))
    return info.rc == mqtt.MQTT_ERR_SUCCESS
