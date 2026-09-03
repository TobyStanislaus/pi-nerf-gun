"""Status LEDs.

The camera loop, the connection callbacks and the decision listener all change
the LEDs, so the pins are owned by one object with a lock instead of being set
up separately on each thread.
"""
import threading

import RPi.GPIO as GPIO

from config import LED_PIN, RED_LED_PIN


class StatusLeds:
    def __init__(self, green_pin=LED_PIN, red_pin=RED_LED_PIN):
        self._green_pin = green_pin
        self._red_pin = red_pin
        self._lock = threading.Lock()
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self._green_pin, GPIO.OUT)
        GPIO.setup(self._red_pin, GPIO.OUT)
        self.red()

    def _set(self, green_on, red_on):
        with self._lock:
            GPIO.output(self._green_pin, GPIO.HIGH if green_on else GPIO.LOW)
            GPIO.output(self._red_pin, GPIO.HIGH if red_on else GPIO.LOW)

    def green(self):
        self._set(True, False)

    def red(self):
        self._set(False, True)

    def off(self):
        self._set(False, False)
