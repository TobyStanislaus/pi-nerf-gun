import base64
import cv2

TOPIC_IMAGE = "image/stream"


def send_image(client, image):
    """Publish one frame on an already-connected client.

    This used to connect and disconnect on every frame - ten times a second -
    using the same client id as the main client, so the broker evicted one
    whenever the other connected.
    """
    _, buffer = cv2.imencode(".jpeg", image, [cv2.IMWRITE_JPEG_QUALITY, 35])
    encoded_image = base64.b64encode(buffer).decode("utf-8")  # Convert to Base64
    client.publish(TOPIC_IMAGE, encoded_image)  # Send via MQTT
