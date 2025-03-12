from tools import *
from servo_control import pull_switch
import cv2
import pigpio
import time
import numpy as np
from picamera2 import Picamera2
from openvino.runtime import Core

# Set up pigpio daemon
pi = pigpio.pi()
if not pi.connected:
    raise RuntimeError("Failed to connect to pigpio daemon!")

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

# Load YOLOv8 ONNX model using OpenVINO
model_path = "model/yolov8n-face.onnx"
ie = Core()
compiled_model = ie.compile_model(model_path, "MYRIAD")  # Use NCS2 for inference
input_layer = compiled_model.input(0)

# Initialize PiCamera2
picam2 = Picamera2()
picam2.configure(picam2.create_still_configuration())
picam2.start()

# Timing lists
image_capture_times = []
processing_times = []
servo_times = []
total_cycle_times_no_switch = []
total_cycle_times_with_switch = []

def preprocess_image(image):
    """ Prepares the image for YOLO inference (resize & normalize). """
    img = cv2.resize(image, (640, 640))  # Resize to YOLO input size
    img = img.astype(np.float32) / 255.0  # Normalize
    img = np.transpose(img, (2, 0, 1))  # Convert to (C, H, W) format
    img = np.expand_dims(img, axis=0)  # Add batch dimension
    return img

def detect_faces(image):
    """Runs inference and returns True if a face is detected."""
    input_data = preprocess_image(image)
    results = compiled_model.infer_new_request({input_layer: input_data})
    
    output = results[compiled_model.output(0)]
    return any(output[:, 4] > 0.3)  # Check confidence score > 0.3

# Capture frames in a loop
try:
    while True:
        cycle_start = time.time()  # Start total cycle timing

        # Capture image
        img_start = time.time()
        image_stream = picam2.capture_array()
        img_end = time.time()
        image_capture_times.append(img_end - img_start)

        # Process the frame using OpenVINO
        proc_start = time.time()
        present = detect_faces(image_stream)
        proc_end = time.time()
        processing_times.append(proc_end - proc_start)

        # Control LEDs
        pi.write(RED_LED_PIN, 0)
        pi.write(LED_PIN, 1)

        if present:
            # Timing for when switch is pulled
            servo_start = time.time()
            
            pi.write(RED_LED_PIN, 1)
            pi.write(LED_PIN, 0)

            pull_switch(SERVO_PIN, pi)
            servo_end = time.time()
            servo_times.append(servo_end - servo_start)

            cycle_end = time.time()
            total_cycle_times_with_switch.append(cycle_end - cycle_start)
        else:
            # Timing for normal cycles without servo activation
            cycle_end = time.time()
            total_cycle_times_no_switch.append(cycle_end - cycle_start)

except KeyboardInterrupt:
    # Print timing statistics when script stops
    print("\n===== TIMING STATISTICS =====")
    print_stats("image_capture", image_capture_times)
    print_stats("processing", processing_times)
    print_stats("pull_switch", servo_times)
    print_stats("total_cycle (no switch)", total_cycle_times_no_switch)
    print_stats("total_cycle (with switch)", total_cycle_times_with_switch)
    print("=============================")

    # Cleanup
    picam2.stop()
    pi.stop()
    cv2.destroyAllWindows()
