#!/bin/bash

# Update and upgrade system packages
sudo apt update && sudo apt upgrade -y

# Install system packages required for libcamera and GPIO
sudo apt install -y \
  python3-venv \
  python3-opencv \
  libatlas-base-dev \
  libjpeg-dev \
  libpng-dev \
  libavcodec-dev \
  libavformat-dev \
  libswscale-dev \
  libv4l-dev \
  v4l-utils \
  libcamera-dev \
  pigpio \
  python3-pigpio \
  python3-rpi.gpio \
  libboost-dev \
  mosquitto \
  mosquitto-clients -y

# Enable camera and pigpio on boot
sudo raspi-config nonint do_camera 0
sudo systemctl enable pigpiod
sudo systemctl start pigpiod

# Set up Python virtual environment named 'venv'
python3 -m venv venv --system-site-packages
source venv/bin/activate

# Upgrade pip and install Python packages inside venv
pip install --upgrade pip 
pip install -r requirements.txt

echo "✅ Virtual environment setup complete!"
echo "To activate it, run: source venv/bin/activate"

# Create systemd service for the Pi Nerf Gun
echo "Creating systemd service..."

sudo bash -c 'cat > /etc/systemd/system/pi-nerf-gun.service << EOF
[Unit]
Description=Pi Nerf Gun Service
After=network.target

[Service]
ExecStart=/home/pi/Documents/pi-nerf-gun/venv/bin/python /home/pi/Documents/pi-nerf-gun/send_pictures.py
WorkingDirectory=/home/pi/Documents/pi-nerf-gun
User=pi
Group=pi
Environment=PATH=/home/pi/Documents/pi-nerf-gun/venv/bin:/usr/bin:/bin
Environment=VIRTUAL_ENV=/home/pi/Documents/pi-nerf-gun/venv
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF'

# Reload systemd, enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable pi-nerf-gun.service
sudo systemctl start pi-nerf-gun.service

echo "✅ Pi Nerf Gun service created and started!"