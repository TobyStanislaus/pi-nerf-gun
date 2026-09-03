"""Reacts to decisions published by the vision machine on response/decision.

The listener shares the caller's MQTT client, pigpio handle and LEDs - it does
not open hardware or connections of its own, so there is exactly one owner of
each resource in the process.
"""
import logging
import threading
import time

from config import COOLDOWN_TIME, SERVO_PIN, STATUS_TIMEOUT
from servo_control import pull_switch

log = logging.getLogger(__name__)


class DecisionListener:
    def __init__(self, pi, leds, servo_pin=SERVO_PIN):
        self._pi = pi
        self._leds = leds
        self._servo_pin = servo_pin
        self._state_lock = threading.Lock()
        self._timer_lock = threading.Lock()
        self._timeout_timer = None
        self._last_pull_time = 0.0
        self._primed = True
        self._firing = False
        self._stopped = False

    # -- MQTT callback -----------------------------------------------------

    def on_message(self, client, userdata, msg):
        try:
            response = msg.payload.decode(errors="replace").strip()
        except Exception:
            log.exception("could not decode payload on %s", msg.topic)
            return

        try:
            self._handle(response)
        except Exception:
            # An exception escaping here kills paho's network thread, which
            # silently stops the whole system until the process is restarted.
            log.exception("error handling response %r", response)
        finally:
            self._reset_timer()

    # -- decision logic ----------------------------------------------------

    def _handle(self, response):
        with self._state_lock:
            now = time.time()
            cooled_down = now - self._last_pull_time > COOLDOWN_TIME

            if response == "stop":
                self._primed = False
                self._leds.red()
                return

            if response == "start":
                self._primed = True

            if response == "shoot" or (response == "true" and self._primed and cooled_down):
                self._last_pull_time = now
                self._fire()
                self._leds.red()
                return

            if self._primed and cooled_down:
                self._leds.green()

    def _fire(self):
        """Move the servo off the network thread.

        pull_switch blocks for ~0.2s; doing that inside the MQTT callback stalls
        keepalives and backs up incoming frames.
        """
        if self._firing:
            return
        self._firing = True
        threading.Thread(target=self._run_servo, daemon=True).start()

    def _run_servo(self):
        try:
            pull_switch(self._servo_pin, self._pi)
        except Exception:
            log.exception("servo pull failed")
        finally:
            self._firing = False

    # -- status timeout ----------------------------------------------------

    def _on_timeout(self):
        """No decision for a while - assume the vision machine is gone."""
        self._leds.red()

    def _reset_timer(self):
        with self._timer_lock:
            if self._stopped:
                return
            if self._timeout_timer is not None:
                self._timeout_timer.cancel()
            self._timeout_timer = threading.Timer(STATUS_TIMEOUT, self._on_timeout)
            self._timeout_timer.daemon = True
            self._timeout_timer.start()

    def start(self):
        self._reset_timer()

    def stop(self):
        with self._timer_lock:
            self._stopped = True
            if self._timeout_timer is not None:
                self._timeout_timer.cancel()
                self._timeout_timer = None
