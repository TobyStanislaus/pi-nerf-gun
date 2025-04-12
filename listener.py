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

    LED_PIN = 17  
    RED_LED_PIN = 15

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(LED_PIN, GPIO.OUT)
    GPIO.setup(RED_LED_PIN, GPIO.OUT)

    def turn_red():
        GPIO.output(LED_PIN, GPIO.LOW)
        GPIO.output(RED_LED_PIN, GPIO.HIGH)

    def turn_green():
        GPIO.output(LED_PIN, GPIO.HIGH)
        GPIO.output(RED_LED_PIN, GPIO.LOW)

    turn_red()

    pi = pigpio.pi()


    timeout_duration = 0.4 
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
            turn_red()
            
        if primed or response == 'start':
            turn_green()

        if response == 'stop':
            turn_red()

        reset_timer()


    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    print("Connecting to MQTT broker...")
    client.connect(BROKER_IP, BROKER_PORT)
    reset_timer()  
    client.loop_forever()