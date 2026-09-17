import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
from picamera2 import Picamera2
import base64
import time
import RPi.GPIO as GPIO
from servo_control import *
from images import *
import cv2
import pigpio
import threading
import os
import sys
from concurrent.futures import TimeoutError as FuturesTimeoutError
from listener import listen
from mqtt_utils import make_client


listener_thread = threading.Thread(target=listen, daemon=True)
listener_thread.start()


def on_connect(client, userdata, flags, rc):
    global is_connected
    if rc == 0:
        is_connected = True
        client.subscribe("response/decision")
 
    else:
        is_connected = False
        GPIO.output(RED_LED_PIN, GPIO.HIGH) 
        GPIO.output(LED_PIN, GPIO.LOW)


def on_disconnect(client, userdata, rc):
    global is_connected
    is_connected = False
    GPIO.output(RED_LED_PIN, GPIO.HIGH)
    GPIO.output(LED_PIN, GPIO.LOW)


def connect_mqtt():
    global is_connected
    # loop_start runs the network thread for the life of the process. The old
    # single client.loop() call returned immediately, so on_disconnect never
    # fired and the broker dropped the socket on keepalive.
    client.loop_start()
    while not is_connected:
        try:
            client.connect(BROKER_IP, BROKER_PORT)
        except Exception:
            GPIO.output(RED_LED_PIN, GPIO.HIGH)
            GPIO.output(LED_PIN, GPIO.LOW)
        time.sleep(RECONNECT_DELAY)


CAPTURE_TIMEOUT = 5.0  # seconds without a frame before we treat the camera as stalled


class CameraStalled(RuntimeError):
    """The camera stopped delivering frames."""


def capture_frame():
    """Capture one frame, giving up if the camera stops delivering.

    picam2.capture_array() waits forever. A stalled pipeline therefore freezes
    the process: nothing is published, nothing is logged, SIGTERM cannot be
    handled and systemd sees a healthy service, so Restart=always never fires.
    A deadline turns that silent freeze into a clean exit and a restart.
    """
    job = picam2.capture_array("main", wait=False)
    try:
        return picam2.wait(job, timeout=CAPTURE_TIMEOUT)
    except (TimeoutError, FuturesTimeoutError):
        raise CameraStalled(f"no frame within {CAPTURE_TIMEOUT}s") from None


def capture_and_publish():
    global is_connected
    
    if is_connected:
        try:
            image = capture_frame()
           
            send_image(client, image)
            # Print timing information
           # print(f"Capture: {capture_time:.4f}s, Encode: {encode_time:.4f}s, Publish: {publish_time:.4f}s, Total: {total_time:.4f}s")
            
        except CameraStalled:
            raise
        except Exception as e:
            print(f"Error capturing or publishing image: {e}")
            GPIO.output(RED_LED_PIN, GPIO.HIGH)
            GPIO.output(LED_PIN, GPIO.LOW)


def boot_pc(BROKER):
    TOPIC = 'run/script'
    SCRIPT_NAME = 'image_processing.py'
    publish.single(TOPIC, SCRIPT_NAME, hostname=BROKER)

# Rest of your initialization code remains the same
BROKER_IP = "127.0.0.1"
#boot_pc(BROKER_IP)

# Set up GPIO
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

servo_pin = 18  # GPIO18 for the servo
pi = pigpio.pi()

if not pi.connected:
    print("pigpio daemon not running - start it with: sudo systemctl start pigpiod")
    exit()

pull_switch(servo_pin, pi)

LED_PIN = 17  # Green LED
RED_LED_PIN = 15
GPIO.setup(LED_PIN, GPIO.OUT)
GPIO.setup(RED_LED_PIN, GPIO.OUT)
GPIO.output(RED_LED_PIN, GPIO.HIGH)
GPIO.output(LED_PIN, GPIO.LOW)

BROKER_PORT = 1883
TOPIC_IMAGE = "image/stream"
TOPIC_RESPONSE = "response/decision"
CLIENT_ID = "raspberry-pi-camera"


COOLDOWN_TIME = 2.0  # Reduced from 2 seconds

CONNECTION_TIMEOUT = 5  # Reduced from 3 seconds
RESPONSE_TIMEOUT = 1.5  # Reduced from 3 seconds
RECONNECT_DELAY = 1.0  # Reduced from 3 seconds
is_connected = False


client = make_client("raspberry-pi-camera")

client.on_connect = on_connect  
client.on_disconnect = on_disconnect


connect_mqtt()
#pull_switch(servo_pin, pi)

# Set up Picamera2
picam2 = Picamera2()
# Optimize camera settings for speed
picam2.configure(picam2.create_still_configuration(
    main={'size': (640, 360)},   # 1080p / 3: fewer pixels, same 16:9 shape the app expects
    lores={'size': (640, 480)},   # Use a reasonable lores resolution


    buffer_count=1,  # Minimum buffer
    display=None,    # No display buffer
    #encode='main'
    encode='lores'   # Low resolution encoding
))

# Enable camera to start in always-on capture mode
picam2.start()


exit_code = 0

try:

    while True:
        capture_and_publish()

        time.sleep(0.1)  # Reduced from 0.1

except KeyboardInterrupt:
    pass
except CameraStalled as e:
    print(f"Camera stalled ({e}) - exiting so systemd restarts us")
    exit_code = 2
finally:
    # Tearing down a stalled camera can block as well, so guarantee the process
    # actually dies - otherwise it keeps holding the camera and the restart
    # inherits the same stall.
    _bail = threading.Timer(10.0, lambda: os._exit(3))
    _bail.daemon = True
    _bail.start()
    picam2.stop()
    client.loop_stop()
    client.disconnect()
    GPIO.cleanup()
    pi.set_servo_pulsewidth(servo_pin, 0)
    pi.stop()

sys.exit(exit_code)