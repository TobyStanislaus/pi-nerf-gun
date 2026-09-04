"""Main loop: capture a frame, publish it, and let the listener act on replies.

One MQTT client, one pigpio handle and one set of GPIO pins for the whole
process. Reconnection is left to paho rather than being hand-rolled.
"""
import logging
import os
import signal
import sys
import threading
import time
from concurrent.futures import TimeoutError as FuturesTimeoutError

import pigpio
import RPi.GPIO as GPIO
from picamera2 import Picamera2

import config
from images import send_image
from leds import StatusLeds
from listener import DecisionListener
from mqtt_utils import make_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("nerf")

_running = True


class CameraStalled(RuntimeError):
    """The camera stopped delivering frames."""


def _request_shutdown(signum, frame):
    # systemd stops the service with SIGTERM; without this the finally block
    # never runs and the servo is left holding a pulse.
    global _running
    log.info("received signal %s, shutting down", signum)
    _running = False


def make_camera():
    picam2 = Picamera2()
    # A video configuration rather than the old still configuration, whose
    # buffer_count=1 could stall. BGR888 matches what create_still_configuration
    # used to hand back, which is the byte order cv2.imencode expects - setting
    # RGB888 here swapped red and blue in the published frames.
    picam2.configure(
        picam2.create_video_configuration(
            main={"size": config.FRAME_SIZE, "format": "BGR888"},
            buffer_count=4,
        )
    )
    picam2.start()
    return picam2


def capture_frame(picam2):
    """Capture one frame, giving up if the camera stops delivering.

    picam2.capture_array() waits forever. If the pipeline stalls - which happens
    when another process is still holding the camera - the main thread blocks
    inside a C call, so nothing is published, no error is logged, and the signal
    handler cannot run. systemd then sees a healthy process and never restarts
    it. A deadline turns that silent wedge into a clean restart.
    """
    job = picam2.capture_array("main", wait=False)
    try:
        return picam2.wait(job, timeout=config.CAPTURE_TIMEOUT)
    except (TimeoutError, FuturesTimeoutError):
        raise CameraStalled(
            f"no frame within {config.CAPTURE_TIMEOUT}s"
        ) from None


def main():
    signal.signal(signal.SIGINT, _request_shutdown)
    signal.signal(signal.SIGTERM, _request_shutdown)

    pi = pigpio.pi()
    if not pi.connected:
        log.error("cannot reach the pigpio daemon - run: sudo systemctl start pigpiod")
        return 1

    leds = StatusLeds()
    listener = DecisionListener(pi, leds)

    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            log.info("connected to broker at %s:%s", config.BROKER_IP, config.BROKER_PORT)
            # Subscribing here (not once at startup) means the subscription is
            # restored after every reconnect.
            client.subscribe(config.TOPIC_RESPONSE)
        else:
            log.warning("connection refused, rc=%s", rc)
            leds.red()

    def on_disconnect(client, userdata, rc):
        log.warning("disconnected from broker, rc=%s - paho will retry", rc)
        leds.red()

    client = make_client(config.CLIENT_ID)
    client.reconnect_delay_set(min_delay=1, max_delay=30)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = listener.on_message
    # connect_async + loop_start reconnects forever on its own, so a broker that
    # is not up yet delays the first frame instead of killing the process.
    client.connect_async(config.BROKER_IP, config.BROKER_PORT, keepalive=config.KEEPALIVE)
    client.loop_start()
    listener.start()

    picam2 = None
    failures = 0
    status = 0
    try:
        picam2 = make_camera()
        log.info("camera started at %sx%s", *config.FRAME_SIZE)

        while _running:
            start = time.monotonic()
            if client.is_connected():
                try:
                    send_image(client, capture_frame(picam2))
                    failures = 0
                except CameraStalled:
                    raise
                except Exception:
                    failures += 1
                    leds.red()
                    if failures in (1, 10) or failures % 100 == 0:
                        log.exception("capture/publish failed (%s in a row)", failures)
                    time.sleep(min(0.1 * failures, 2.0))

            elapsed = time.monotonic() - start
            time.sleep(max(0.0, config.FRAME_INTERVAL - elapsed))
    except CameraStalled as exc:
        log.error("camera stalled (%s) - exiting so systemd restarts us", exc)
        status = 2
    finally:
        # Tearing down a stalled camera can block too. Guarantee the process
        # actually dies, otherwise systemd waits on a corpse that holds the
        # camera and every restart inherits the same wedge.
        bail = threading.Timer(10.0, lambda: os._exit(3))
        bail.daemon = True
        bail.start()
        log.info("cleaning up")
        listener.stop()
        client.loop_stop()
        try:
            client.disconnect()
        except Exception:
            pass
        if picam2 is not None:
            try:
                picam2.stop()
                picam2.close()
            except Exception:
                log.exception("error stopping the camera")
        leds.off()
        pi.set_servo_pulsewidth(config.SERVO_PIN, 0)
        pi.stop()
        GPIO.cleanup()
    return status


if __name__ == "__main__":
    sys.exit(main())
