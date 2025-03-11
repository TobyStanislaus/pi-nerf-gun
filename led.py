import RPi.GPIO as GPIO
import time

# Use BCM pin numbering
GPIO.setmode(GPIO.BCM)

# Set GPIO 17 as an output
LED_PIN = 17
GPIO.setup(LED_PIN, GPIO.OUT)
while True:

    print("Turning LED on...")
    GPIO.output(LED_PIN, GPIO.HIGH)
    time.sleep(0.2)  # LED stays on for 2 seconds

    print("Turning LED off...")
    GPIO.output(LED_PIN, GPIO.LOW)
    time.sleep(0.2)  # LED stays on for 2 seconds

# Cleanup
GPIO.cleanup()
