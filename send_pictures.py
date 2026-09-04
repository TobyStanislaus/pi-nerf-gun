"""Main loop: capture a frame, publish it, and let the listener act on replies.

One MQTT client, one pigpio handle and one set of GPIO pins for the whole
process. Reconnection is left to paho rather than being hand-rolled.
"""
import logging
import signal
import sys
import time

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


def _request_shutdown(signum, frame):
    # systemd stops the service with SIGTERM; without this the finally block
    # never runs and the servo is left holding a pulse.
    global _running
    log.info("received signal %s, shutting down", signum)
    _running = False


def make_camera():
    picam2 = Picamera2()
    # A video configuration at the size we actually publish. The old still
    # configuration captured 1920x1080 ten times a second and base64'd the whole
    # frame onto the wire, which is what filled the client's send queue.
    picam2.configure(
        picam2.create_video_configuration(
            main={"size": config.FRAME_SIZE, "format": "RGB888"},
            # Pin the sensor mode: left to itself libcamera picks the imx708's
            # 1536x864 binned mode, which logs "PDAF data in unsupported format"
            # every frame and gives up on phase-detect autofocus.
            raw={"size": config.RAW_SIZE},
            buffer_count=4,
        )
    )
    picam2.start()
    return picam2


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
    try:
        picam2 = make_camera()
        log.info("camera started at %sx%s", *config.FRAME_SIZE)

        while _running:
            start = time.monotonic()
            if client.is_connected():
                try:
                    send_image(client, picam2.capture_array())
                    failures = 0
                except Exception:
                    failures += 1
                    leds.red()
                    if failures in (1, 10) or failures % 100 == 0:
                        log.exception("capture/publish failed (%s in a row)", failures)
                    time.sleep(min(0.1 * failures, 2.0))

            elapsed = time.monotonic() - start
            time.sleep(max(0.0, config.FRAME_INTERVAL - elapsed))
    finally:
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
