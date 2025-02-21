#!/home/pi/Documents/send_pics/venv/bin/python
import paho.mqtt.client as mqtt
from picamera2 import Picamera2
import io
import base64
import time
import RPi.GPIO as GPIO
from servo_control import *
import cv2

# Set up GPIO
GPIO.setwarnings(False)
servo_pin = 18  # Use GPIO18 (you can change this)
GPIO.setmode(GPIO.BCM)
GPIO.setup(servo_pin, GPIO.OUT)

# Set up PWM
pwm = GPIO.PWM(servo_pin, 40)  # 50 Hz PWM signal
pwm.start(0)


LED_PIN = 17
GPIO.setup(LED_PIN, GPIO.OUT)

BROKER_IP = "192.168.0.155"
BROKER_PORT = 1883
TOPIC_IMAGE = "image/stream"
TOPIC_RESPONSE = "response/decision"
CLIENT_ID = "raspberry-pi-camera"

last_shot_time = 0  # Initialize last shot time
COOLDOWN_TIME = 5  # Cooldown time in seconds

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to broker.")
        client.subscribe(TOPIC_RESPONSE)  # Subscribe to receive responses
    else:
        print(f"Connection failed with code {rc}")


def on_message(client, userdata, msg):
    global last_shot_time
    current_time = time.time()
    
    if current_time - last_shot_time >= COOLDOWN_TIME:
        response = msg.payload.decode()
        if response == 'yes':
            pull_switch(servo_pin, pwm)
            last_shot_time = current_time  # Update last shot time
            GPIO.output(LED_PIN, GPIO.LOW)

        print(f"Received response: {response}")
        GPIO.output(LED_PIN, GPIO.HIGH)
    else:
        GPIO.output(LED_PIN, GPIO.LOW)
        print("Cooldown active. Cannot shoot yet.")
    
client = mqtt.Client(client_id=CLIENT_ID, callback_api_version=mqtt.CallbackAPIVersion.VERSION1)
client.on_connect = on_connect  
client.on_message = on_message

client.connect(BROKER_IP, BROKER_PORT)
client.loop_start()

# Set up Picamera2
picam2 = Picamera2()
picam2.configure(picam2.create_still_configuration(main={'size': (320, 240)}))
picam2.start()

def capture_and_publish():
    image = picam2.capture_array()
    _, buffer = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 50])
    encoded_image = base64.b64encode(buffer).decode()
    client.publish(TOPIC_IMAGE, encoded_image)

try:
    while True:
        capture_and_publish()
        time.sleep(0.1)  # Reduce frame rate to avoid flooding

except KeyboardInterrupt:
    print("Stopping...")
finally:
    picam2.stop()
    client.loop_stop()
    client.disconnect()
    GPIO.cleanup()
