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

## Running the System

Start the MQTT broker, then run:

```bash
python send_pictures.py
```

This will:

1. Start the MQTT listener in a separate thread.
2. Initialise the GPIO pins and servo.
3. Initialise the Raspberry Pi camera.
4. Continuously capture images.
5. Compress and encode each image.
6. Publish the image to the MQTT image stream.
7. Wait for responses from the external image processing system.
8. Fire the Nerf gun when an appropriate response is received.

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
├── images.py             # Image compression, encoding and MQTT publishing
├── listener.py           # MQTT response listener and LED control
├── servo_control.py      # Servo movement and trigger control
├── led.py                # LED functionality
├── requirements.txt      # Python dependencies
├── setup.sh              # Setup script
└── test.jpeg             # Test image
```

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

* Configurable MQTT broker addresses
* Environment variables or configuration files
* Better error handling and reconnection logic
* Camera frame rate optimisation
* Authentication for MQTT communication
* Logging and diagnostics
* A systemd service for automatic startup
* More sophisticated firing and safety logic

## Related Project

This repository represents the Raspberry Pi hardware and communication component of a larger computer vision system. The Pi captures images and handles the physical trigger mechanism, while an external machine performs the image processing and returns decisions via MQTT.
