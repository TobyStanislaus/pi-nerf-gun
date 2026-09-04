# Raspberry Pi Computer Vision Nerf Gun

A Raspberry Pi-based Nerf gun control system that captures images, sends them to an external computer vision system using MQTT, and fires the Nerf gun when a positive detection is returned.

The project forms the Raspberry Pi side of a distributed computer vision pipeline. The Raspberry Pi handles image capture, communication, GPIO control, and actuation, while image processing can be performed externally.

## How It Works

The system follows this pipeline:

```text
Raspberry Pi Camera
        │
        ▼
 Capture Image
        │
        ▼
 Compress & Encode Image
        │
        ▼
 MQTT: image/stream
        │
        ▼
 External Computer Vision System
        │
        ▼
 MQTT: response/decision
        │
        ▼
 Raspberry Pi Listener
        │
        ├──► Status LEDs
        │
        └──► Servo Motor → Nerf Gun Trigger
```

The Raspberry Pi continuously captures images using the Pi Camera. Each frame is JPEG-compressed, Base64 encoded, and published to the MQTT topic:

```text
image/stream
```

An external system processes the image and publishes a response to:

```text
response/decision
```

Depending on the response, the Raspberry Pi can arm the system, fire the Nerf gun, or stop it.

## Features

* Raspberry Pi camera capture using `Picamera2`
* Image compression with OpenCV
* Image transmission over MQTT
* Base64 image encoding
* Servo-controlled Nerf gun trigger
* GPIO-controlled status LEDs
* Separate MQTT listener running in its own thread
* Automatic status timeout
* Basic cooldown logic to prevent repeated firing

## Hardware

The project is designed to run on a Raspberry Pi with:

* Raspberry Pi
* Raspberry Pi Camera
* Servo motor connected to the Nerf gun trigger
* Green status LED
* Red status LED
* MQTT broker running on the local network or Raspberry Pi

### GPIO Pins

| Component | GPIO Pin |
| --------- | -------: |
| Servo     |  GPIO 18 |
| Green LED |  GPIO 17 |
| Red LED   |  GPIO 15 |

The servo is controlled using `pigpio`.

## Configuration

Everything configurable lives in `config.py` and can be overridden with
environment variables, so nothing has to be edited to point the Pi at a
different broker:

| Variable | Default | Purpose |
| -------- | ------- | ------- |
| `NERF_BROKER_IP` | `127.0.0.1` | MQTT broker address |
| `NERF_BROKER_PORT` | `1883` | MQTT broker port |
| `NERF_SERVO_PIN` | `18` | Servo GPIO pin |
| `NERF_LED_PIN` | `17` | Green LED pin |
| `NERF_RED_LED_PIN` | `15` | Red LED pin |
| `NERF_FRAME_WIDTH` / `NERF_FRAME_HEIGHT` | `1920` / `1080` | Published frame size |
| `NERF_FRAME_INTERVAL` | `0.1` | Seconds between frames |
| `NERF_JPEG_QUALITY` | `35` | JPEG quality |
| `NERF_COOLDOWN` | `1.0` | Minimum seconds between shots |
| `NERF_STATUS_TIMEOUT` | `0.4` | Seconds of silence before the red LED comes back |

Under systemd, add them as `Environment=` lines in the unit file.

## Installation

Clone the repository:

```bash
git clone https://github.com/TobyStanislaus/pi-nerf-gun.git
cd pi-nerf-gun
```

Install the Python dependencies:

```bash
pip install -r requirements.txt
```

The project uses:

* `paho-mqtt`
* `opencv-python-headless`
* `picamera2`
* `RPi.GPIO`
* `pigpio`

Make sure the `pigpio` daemon is running:

```bash
sudo pigpiod
```

An MQTT broker such as Mosquitto is also required.

Mosquitto 2.x binds to localhost only unless a listener is configured, so a
default install can be reached from the Pi but not from a phone or the vision
machine. `setup.sh` writes `/etc/mosquitto/conf.d/lan.conf`:

```text
listener 1883 0.0.0.0
allow_anonymous true
```

Check what the broker is actually bound to with `ss -tlnp | grep 1883`.

This leaves the broker open to anything on the local network - on an untrusted
network, add authentication with `mosquitto_passwd` and set
`allow_anonymous false`. Do not forward port 1883 on your router: the camera
stream and the trigger topic are both unauthenticated and unencrypted.

## Running the System

Start the MQTT broker, then run:

```bash
python send_pictures.py
```

This will:

1. Connect to `pigpio` and fail fast with a clear message if the daemon is down.
2. Initialise the GPIO pins and status LEDs.
3. Connect to the MQTT broker, retrying with backoff until it is available.
4. Initialise the Raspberry Pi camera.
5. Continuously capture, compress, encode and publish frames.
6. Handle responses from the external image processing system.
7. Fire the Nerf gun when an appropriate response is received.

The process shuts down cleanly on both `Ctrl-C` and `SIGTERM` (the signal
`systemctl stop` sends), releasing the servo pulse and the GPIO pins.

### Troubleshooting

* **Exits immediately with a pigpio message** - run `sudo systemctl start pigpiod`.
* **Red LED never turns green** - nothing is publishing on `response/decision`.
  Check with `mosquitto_sub -t 'response/decision' -v`.
* **Logs** - `journalctl -u pi-nerf-gun -f`.

## MQTT Communication

### Image Stream

Captured images are published to:

```text
image/stream
```

The images are JPEG-compressed and Base64 encoded before transmission.

### Decision Responses

The Raspberry Pi listens on:

```text
response/decision
```

Supported responses include:

| Response | Action                                    |
| -------- | ----------------------------------------- |
| `true`   | Fire the Nerf gun if the system is primed |
| `shoot`  | Fire the Nerf gun                         |
| `start`  | Prime the system                          |
| `stop`   | Disable firing                            |

The status LEDs provide visual feedback about the state of the system.

## Project Structure

```text
pi-nerf-gun/
│
├── send_pictures.py      # Main application and camera loop
├── config.py             # Broker, pins and timings (env-var overridable)
├── images.py             # Image compression, encoding and MQTT publishing
├── listener.py           # Decision handling and firing logic
├── leds.py               # Status LED control
├── mqtt_utils.py         # paho-mqtt 1.x / 2.x compatibility
├── servo_control.py      # Servo movement and trigger control
├── blink_test.py         # Standalone LED sanity check
├── requirements.txt      # Python dependencies
├── setup.sh              # Setup script
└── test.jpeg             # Test image
```

The whole process uses a single MQTT client, a single `pigpio` handle and a
single set of GPIO pins. The decision listener runs on paho's network thread
rather than opening a second connection of its own, and servo movement is
handed off to a short-lived worker so the network loop is never blocked.

## Servo Control

The Nerf gun trigger is controlled using a servo connected to GPIO 18.

The servo movement is handled by `servo_control.py`, which converts an angle into a PWM pulse width and moves the servo through a short sequence to pull and release the trigger.

## External Computer Vision

This repository contains the Raspberry Pi control and communication side of the system.

The intended workflow is for another machine to:

1. Subscribe to `image/stream`.
2. Decode and process incoming images.
3. Run a computer vision or machine learning model.
4. Publish a decision to `response/decision`.

This allows computationally intensive image processing to run on more powerful hardware while the Raspberry Pi handles the camera and physical actuation.

## Technologies

* Python
* Raspberry Pi
* Picamera2
* OpenCV
* MQTT
* Paho MQTT
* RPi.GPIO
* pigpio

## Future Improvements

Possible improvements include:

* Authentication and TLS for MQTT communication
* Adaptive frame rate based on broker backpressure
* A hardware arming switch in series with the servo
* More sophisticated firing and safety logic

## Related Project

This repository represents the Raspberry Pi hardware and communication component of a larger computer vision system. The Pi captures images and handles the physical trigger mechanism, while an external machine performs the image processing and returns decisions via MQTT.
