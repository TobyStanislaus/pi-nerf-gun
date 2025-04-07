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
  libboost-dev

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