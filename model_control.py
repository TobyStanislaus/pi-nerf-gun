from tools import *
from servo_control import *
import cv2
import RPi.GPIO as GPIO
import time
from picamera2 import Picamera2
import numpy as np

# Set up GPIO
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

LED_PIN = 17  # Green LED
RED_LED_PIN = 24
GPIO.setup(LED_PIN, GPIO.OUT)
GPIO.setup(RED_LED_PIN, GPIO.OUT)

GPIO.output(RED_LED_PIN, GPIO.LOW)
GPIO.output(LED_PIN, GPIO.LOW)

model_path = 'model/yolov8n-face.pt'
model = load_model(model_path)

# Suppress OpenCV warnings
GPIO.setwarnings(False)
servo_pin = 18
GPIO.setmode(GPIO.BCM)
GPIO.setup(servo_pin, GPIO.OUT)
pwm = GPIO.PWM(servo_pin, 50)
pwm.start(0)

# Initialize PiCamera2
picam2 = Picamera2()

# Set camera resolution (optional)
picam2.configure(picam2.create_still_configuration())

# Start the camera
picam2.start()

# Give the camera a moment to initialize
time.sleep(2)

# Capture frames in a loop
while True:
    # Capture image from the camera into a NumPy array
    image_stream = picam2.capture_array()

    # Process the frame using OpenCV
    present = detect_image(model, image_stream)

    if present:
        #pull_switch(servo_pin, pwm)
        print('shoot')

# Stop the camera and clean up
picam2.stop()
cv2.destroyAllWindows()
