from tools import *
from servo_control import pull_switch
import cv2
import pigpio
import time
from picamera2 import Picamera2
import numpy as np

# Set up pigpio daemon
pi = pigpio.pi()  # Connect to local Pi's pigpio daemon

# Define GPIO pins
LED_PIN = 17  # Green LED
RED_LED_PIN = 24
SERVO_PIN = 18  # Servo control pin

# Set up GPIO output for LEDs
pi.set_mode(LED_PIN, pigpio.OUTPUT)
pi.set_mode(RED_LED_PIN, pigpio.OUTPUT)

# Turn off LEDs initially
pi.write(RED_LED_PIN, 0)
pi.write(LED_PIN, 0)

# Load YOLOv8 model
model_path = 'model/yolov8n-face.pt'
model = load_model(model_path)

# Initialize PiCamera2
picam2 = Picamera2()
picam2.configure(picam2.create_still_configuration())
picam2.start()

# Capture frames in a loop
while True:
    # Capture image from the camera into a NumPy array
    image_stream = picam2.capture_array()

    # Process the frame using OpenCV
    present = detect_image(model, image_stream)
    pi.write(RED_LED_PIN, 0)
    pi.write(LED_PIN, 1)

    if present:

        pi.write(RED_LED_PIN, 1)
        pi.write(LED_PIN, 0)
        pull_switch(SERVO_PIN, pi)  # Call pull_switch from servo_control.py

        time.sleep(1)

# Cleanup
picam2.stop()
pi.stop()
cv2.destroyAllWindows()
