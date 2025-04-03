import paho.mqtt.client as mqtt
from servo_control import *
import RPi.GPIO as GPIO
import pigpio
import threading
import time

def listen():
    servo_pin = 18 
    BROKER_IP = "127.0.0.1"  
    BROKER_PORT = 1883
    TOPIC = "response/decision"

    LED_PIN = 17  # Green LED
    RED_LED_PIN = 15

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(LED_PIN, GPIO.OUT)
    GPIO.setup(RED_LED_PIN, GPIO.OUT)

    # Default LED state: Red ON, Green OFF
    GPIO.output(RED_LED_PIN, GPIO.HIGH)
    GPIO.output(LED_PIN, GPIO.LOW)

    pi = pigpio.pi()

    # Timer to track message timeout
    timeout_duration = 1  # Change this to set the delay (in seconds)
    global last_pull_time, timeout_timer
    last_pull_time = 0
    timeout_timer = None

    def reset_timer():
        """Resets the timer each time a message is received."""
        global timeout_timer
        if timeout_timer:
            timeout_timer.cancel()  # Cancel the previous timer
        timeout_timer = threading.Timer(timeout_duration, turn_red)
        timeout_timer.start()

    def turn_red():
        """Turn the green light ON and red light OFF after timeout."""
        GPIO.output(LED_PIN, GPIO.LOW)
        GPIO.output(RED_LED_PIN, GPIO.HIGH)
        print("No response received, turning green light ON.")

    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT broker!")
            client.subscribe(TOPIC)
        else:
            print(f"Failed to connect, return code {rc}")

    def on_message(client, userdata, msg):
        global timeout_timer, last_pull_time

        response = msg.payload.decode()

        current_time = time.time()
        if response == 'true' and current_time-last_pull_time>1:
            pull_switch(servo_pin, pi)
            last_pull_time=current_time
            GPIO.output(RED_LED_PIN, GPIO.HIGH)
            GPIO.output(LED_PIN, GPIO.LOW)
        else:  
            GPIO.output(RED_LED_PIN, GPIO.LOW)
            GPIO.output(LED_PIN, GPIO.HIGH)

        reset_timer()


    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    print("Connecting to MQTT broker...")
    client.connect(BROKER_IP, BROKER_PORT)
    reset_timer()  
    client.loop_forever()