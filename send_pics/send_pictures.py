import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
from picamera2 import Picamera2
import base64
import time
import RPi.GPIO as GPIO
from servo_control import *
import cv2
import os
import pigpio

os.system("sudo pigpiod")

def on_connect(client, userdata, flags, rc):
    global is_connected
    if rc == 0:
        is_connected = True
        update_led_status()
        client.subscribe(TOPIC_RESPONSE)
    else:
        is_connected = False
        GPIO.output(RED_LED_PIN, GPIO.HIGH) 
        GPIO.output(LED_PIN, GPIO.LOW) 


def on_disconnect(client, userdata, rc):
    global is_connected
    is_connected = False

    GPIO.output(RED_LED_PIN, GPIO.HIGH)  # Indicate connection loss
    GPIO.output(LED_PIN, GPIO.LOW)  # Ensure green LED is off


def on_message(client, userdata, msg):
    global last_shot_time, last_response_time
    current_time = time.time()
    
    # Update last response time when any message is received
    last_response_time = current_time
    
    if current_time - last_shot_time >= COOLDOWN_TIME:
        response = msg.payload.decode()
        #print(f"Received response: {response}")
        
        GPIO.output(LED_PIN, GPIO.HIGH)
        GPIO.output(RED_LED_PIN, GPIO.LOW)

        if response == 'yes':
            # Turn red LED on and green LED off when shooting
            GPIO.output(RED_LED_PIN, GPIO.HIGH)
            GPIO.output(LED_PIN, GPIO.LOW)
            
            pull_switch(servo_pin, pi)
            last_shot_time = current_time


def update_led_status():
    """Update LEDs based on system state"""
    current_time = time.time()
    
    # Check if system is not connected
    if not is_connected or (current_time - last_response_time > RESPONSE_TIMEOUT):
        # System error state - red on, green off
        GPIO.output(RED_LED_PIN, GPIO.HIGH)
        GPIO.output(LED_PIN, GPIO.LOW)
        return
    

def connect_mqtt():
    global is_connected
    while not is_connected:
        try:
            client.connect(BROKER_IP, BROKER_PORT)
            client.loop_start()
            time.sleep(RECONNECT_DELAY)  
        except Exception as e:
            GPIO.output(RED_LED_PIN, GPIO.HIGH)
            GPIO.output(LED_PIN, GPIO.LOW) 
            time.sleep(RECONNECT_DELAY)


def capture_and_publish():
    global last_successful_publish, is_connected, latency
    
    if is_connected:
        try:
            image = picam2.capture_array()
            _, buffer = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 50])
            encoded_image = base64.b64encode(buffer).decode()
            client.publish(TOPIC_IMAGE, encoded_image)
            last_successful_publish = time.time()
        except Exception as e:
            #print(f"Error capturing or publishing image: {e}")
            GPIO.output(RED_LED_PIN, GPIO.HIGH)  # Indicate error with RED LED
            GPIO.output(LED_PIN, GPIO.LOW)  # Ensure green LED is off


def check_connection_and_responses():
    global is_connected, last_response_time
    current_time = time.time()
    
    # Check for connection timeout
    if current_time - last_successful_publish > CONNECTION_TIMEOUT:
        is_connected = False
        #print("Connection lost! No successful publish in", CONNECTION_TIMEOUT, "seconds.")
        GPIO.output(RED_LED_PIN, GPIO.HIGH)  # Indicate connection loss
        GPIO.output(LED_PIN, GPIO.LOW)  # Ensure green LED is off
        connect_mqtt()  # Attempt to reconnect
    
    # Update LED status based on system state
    update_led_status()


def boot_pc(BROKER):
    TOPIC = 'run/script'
    SCRIPT_NAME = 'image_processing.py'
    publish.single(TOPIC, SCRIPT_NAME, hostname=BROKER)

BROKER_IP = "192.168.0.155"

boot_pc(BROKER_IP)

# Set up GPIO
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

servo_pin = 18  # GPIO18 for the servo
pi = pigpio.pi()

if not pi.connected:
    exit()

latency = {}

LED_PIN = 17  # Green LED
RED_LED_PIN = 24
GPIO.setup(LED_PIN, GPIO.OUT)
GPIO.setup(RED_LED_PIN, GPIO.OUT)
GPIO.output(RED_LED_PIN, GPIO.HIGH)  # Initialize RED LED to ON until connection established
GPIO.output(LED_PIN, GPIO.LOW)  # Ensure green LED is off initially

BROKER_IP = "192.168.0.155"
BROKER_PORT = 1883
TOPIC_IMAGE = "image/stream"
TOPIC_RESPONSE = "response/decision"
CLIENT_ID = "raspberry-pi-camera"

last_shot_time = 0  # Initialize last shot time
last_response_time = time.time()  # Initialize last response time
COOLDOWN_TIME = 2  # Cooldown time in seconds
last_successful_publish = time.time()
CONNECTION_TIMEOUT = 3  # Time in seconds before assuming connection is lost
RESPONSE_TIMEOUT = 3  # Time in seconds before assuming server not responding
RECONNECT_DELAY = 3  # Time to wait before trying to reconnect
is_connected = False  # Track connection status

client = mqtt.Client(client_id=CLIENT_ID, callback_api_version=mqtt.CallbackAPIVersion.VERSION1)
client.on_connect = on_connect  
client.on_disconnect = on_disconnect
client.on_message = on_message


connect_mqtt()  # Initial connection attempt

# Set up Picamera2
picam2 = Picamera2()
picam2.configure(picam2.create_still_configuration(main={'size': (320, 240)}))
picam2.start()

try:
    while True:
        capture_and_publish()
        check_connection_and_responses()
        time.sleep(0.1)

except KeyboardInterrupt:
    pass
finally:
    picam2.stop()
    client.loop_stop()
    client.disconnect()
    GPIO.cleanup()
    pi.set_servo_pulsewidth(servo_pin, 0)
    pi.stop()