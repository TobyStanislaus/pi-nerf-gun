import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
from picamera2 import Picamera2
import base64
import time
import RPi.GPIO as GPIO
from servo_control import *
import cv2
import pigpio
import statistics  # For calculating averages and statistics of timings

# Dictionary to store timing data
timings = {
    "image_capture": [],
    "encoding": [],
    "mqtt_publish": [],
    "total_publish": [],
    "response_latency": [],  # Time between publishing and receiving response
    "pull_switch": []  # Time taken to pull the switch
}

def on_connect(client, userdata, flags, rc):
    global is_connected
    if rc == 0:
        is_connected = True
        update_led_status()
        client.subscribe(TOPIC_RESPONSE)
 
    else:
        is_connected = False
        GPIO.output(RED_LED_PIN, GPIO.HIGH) 
        GPIO.output(LED_PIN, GPIO.LOW)


def on_disconnect(client, userdata, rc):
    global is_connected
    is_connected = False
    GPIO.output(RED_LED_PIN, GPIO.HIGH)
    GPIO.output(LED_PIN, GPIO.LOW)


def on_message(client, userdata, msg):
    global last_shot_time, last_response_time, last_publish_time
    current_time = time.time()
    
    # Calculate response latency (time from publish to response)
    if hasattr(client, 'last_publish_time'):
        response_time = current_time - client.last_publish_time
        timings["response_latency"].append(response_time)
        #print(f"Response latency: {response_time:.4f} seconds")
    
    # Update last response time
    last_response_time = current_time
    
    if current_time - last_shot_time >= COOLDOWN_TIME:
        response = msg.payload.decode()
        
        #print(f"Received response: {response}")
        
        GPIO.output(LED_PIN, GPIO.HIGH)
        GPIO.output(RED_LED_PIN, GPIO.LOW)

        if response == 'yes':
            # Turn red LED on and green LED off when shooting
            GPIO.output(RED_LED_PIN, GPIO.HIGH)
            GPIO.output(LED_PIN, GPIO.LOW)
            
            # Time the pull_switch operation
            start_pull = time.time()
            pull_switch(servo_pin, pi)
            end_pull = time.time()
            
            pull_time = end_pull - start_pull
            timings["pull_switch"].append(pull_time)
            #print(f"Switch pull time: {pull_time:.4f} seconds")
            
            last_shot_time = current_time

def update_led_status():
    """Update LEDs based on system state"""
    current_time = time.time()
    
    if not is_connected or (current_time - last_response_time > RESPONSE_TIMEOUT):
        GPIO.output(RED_LED_PIN, GPIO.HIGH)
        GPIO.output(LED_PIN, GPIO.LOW)
        return

def connect_mqtt():
    global is_connected
    while not is_connected:
        try:
            client.connect(BROKER_IP, BROKER_PORT, keepalive=5)
            client.loop_start()
            time.sleep(RECONNECT_DELAY)  
        except Exception as e:
            GPIO.output(RED_LED_PIN, GPIO.HIGH)
            GPIO.output(LED_PIN, GPIO.LOW) 
            time.sleep(RECONNECT_DELAY)

def capture_and_publish():
    global last_successful_publish, is_connected
    
    if is_connected:
        try:
            # Time image capture
            start_capture = time.time()
            image = picam2.capture_array()
            end_capture = time.time()
            capture_time = end_capture - start_capture
            timings["image_capture"].append(capture_time)
            
            # Time encoding
            start_encode = time.time()
            _, buffer = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 35])
            encoded_image = base64.b64encode(buffer).decode()
            end_encode = time.time()
            encode_time = end_encode - start_encode
            timings["encoding"].append(encode_time)
            
            # Time MQTT publish
            start_publish = time.time()
            client.publish(TOPIC_IMAGE, encoded_image)
            end_publish = time.time()
            publish_time = end_publish - start_publish
            timings["mqtt_publish"].append(publish_time)
            
            # Total time for the entire publish operation
            total_time = end_publish - start_capture
            timings["total_publish"].append(total_time)
            
            # Store the publish time for calculating response latency
            client.last_publish_time = end_publish
            
            last_successful_publish = time.time()
            
            # Print timing information
           # print(f"Capture: {capture_time:.4f}s, Encode: {encode_time:.4f}s, Publish: {publish_time:.4f}s, Total: {total_time:.4f}s")
            
        except Exception as e:
            print(f"Error capturing or publishing image: {e}")
            GPIO.output(RED_LED_PIN, GPIO.HIGH)
            GPIO.output(LED_PIN, GPIO.LOW)


def check_connection_and_responses():
    global is_connected, last_response_time
    current_time = time.time()
    
    if current_time - last_successful_publish > CONNECTION_TIMEOUT:
        is_connected = False
        GPIO.output(RED_LED_PIN, GPIO.HIGH)
        GPIO.output(LED_PIN, GPIO.LOW)
        connect_mqtt()
    
    update_led_status()

def print_timing_stats():
    """Print statistics for all timing measurements"""
    print("\n===== TIMING STATISTICS =====")
    for category, times in timings.items():
        if times:
            avg = statistics.mean(times)
            if len(times) > 1:
                stdev = statistics.stdev(times)
                min_time = min(times)
                max_time = max(times)
                print(f"{category}: avg={avg:.4f}s, min={min_time:.4f}s, max={max_time:.4f}s, stdev={stdev:.4f}s (samples: {len(times)})")
            else:
                print(f"{category}: {avg:.4f}s (only 1 sample)")
        else:
            print(f"{category}: No data")
    print("=============================\n")

def boot_pc(BROKER):
    TOPIC = 'run/script'
    SCRIPT_NAME = 'image_processing.py'
    publish.single(TOPIC, SCRIPT_NAME, hostname=BROKER)

# Rest of your initialization code remains the same
BROKER_IP = "192.168.0.155"
boot_pc(BROKER_IP)

# Set up GPIO
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

servo_pin = 18  # GPIO18 for the servo
pi = pigpio.pi()

if not pi.connected:
    exit()

LED_PIN = 17  # Green LED
RED_LED_PIN = 24
GPIO.setup(LED_PIN, GPIO.OUT)
GPIO.setup(RED_LED_PIN, GPIO.OUT)
GPIO.output(RED_LED_PIN, GPIO.HIGH)
GPIO.output(LED_PIN, GPIO.LOW)

BROKER_PORT = 1883
TOPIC_IMAGE = "image/stream"
TOPIC_RESPONSE = "response/decision"
CLIENT_ID = "raspberry-pi-camera"

last_shot_time = 0
last_response_time = time.time()
COOLDOWN_TIME = 2.0  # Reduced from 2 seconds
last_successful_publish = time.time()
CONNECTION_TIMEOUT = 1.5  # Reduced from 3 seconds
RESPONSE_TIMEOUT = 1.5  # Reduced from 3 seconds
RECONNECT_DELAY = 1.0  # Reduced from 3 seconds
is_connected = False

client = mqtt.Client(client_id=CLIENT_ID, callback_api_version=mqtt.CallbackAPIVersion.VERSION1)
client.on_connect = on_connect  
client.on_disconnect = on_disconnect
client.on_message = on_message

connect_mqtt()
pull_switch(servo_pin, pi)

# Set up Picamera2
picam2 = Picamera2()
# Optimize camera settings for speed
picam2.configure(picam2.create_still_configuration(
    main={'size': (160, 120)},  # Even smaller resolution
    lores={'size': (160, 120)},

    buffer_count=1,  # Minimum buffer
    display=None,    # No display buffer
    #encode='main'
    encode='lores'   # Low resolution encoding
))

# Enable camera to start in always-on capture mode
picam2.start()

timing_report_interval = 30  # Print timing stats every 30 seconds
last_timing_report = time.time()

try:
    while True:
        capture_and_publish()
        check_connection_and_responses()
        
        # Print timing statistics periodically
        current_time = time.time()
        if current_time - last_timing_report > timing_report_interval:
            #print_timing_stats()
            last_timing_report = current_time
            
        time.sleep(0.05)  # Reduced from 0.1

except KeyboardInterrupt:
    print_timing_stats()  # Print final stats on exit
    pass
finally:
    picam2.stop()
    client.loop_stop()
    client.disconnect()
    GPIO.cleanup()
    pi.set_servo_pulsewidth(servo_pin, 0)
    pi.stop()