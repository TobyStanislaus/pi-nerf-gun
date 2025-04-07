import paho.mqtt.client as mqtt
import os
import base64
import time
import cv2


print("✅ All images sent.")


def send_image(image):
    BROKER_IP = "127.0.0.1"
    BROKER_PORT = 1883
    TOPIC_IMAGE = "image/stream"
    client = mqtt.Client(client_id="Image-sender")
    client.connect(BROKER_IP, BROKER_PORT)


    _, buffer = cv2.imencode(".jpeg", image, [cv2.IMWRITE_JPEG_QUALITY, 35])

    encoded_image = base64.b64encode(buffer).decode("utf-8")  # Convert to Base64 
    client.publish(TOPIC_IMAGE, encoded_image)  # Send via MQTT


    client.disconnect()

