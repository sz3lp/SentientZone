#!/bin/bash
set -euo pipefail

LOGFILE="install.log"
exec > >(tee -a "$LOGFILE") 2>&1

BASE_DIR="${SZ_BASE_DIR:-/home/pi/sz}"
SZ_USER="${SZ_USER:-pi}"
VENV_DIR="$BASE_DIR/venv"
REQUIREMENTS="$BASE_DIR/requirements.txt"
SERVICE_FILE="$BASE_DIR/sz_ui.service"
STATE_DIR="$BASE_DIR/state"
LOG_DIR="$BASE_DIR/logs"

echo "Starting SentientZone setup..."

# If SZ_API_KEY is set, store it in a secrets file
if [ -n "${SZ_API_KEY:-}" ]; then
    mkdir -p "$BASE_DIR/config"
    echo "$SZ_API_KEY" > "$BASE_DIR/config/api_key.secret"
    chmod 600 "$BASE_DIR/config/api_key.secret"
fi

# Create folders
mkdir -p "$STATE_DIR" "$LOG_DIR"

# Install system packages
sudo apt-get update -y
sudo apt-get install -y python3-venv python3-pip git raspi-gpio python3-rpi.gpio
sudo pip3 install Adafruit_DHT

# Create virtual environment
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi
"$VENV_DIR/bin/pip" install --upgrade pip

if [ -f "$REQUIREMENTS" ]; then
    "$VENV_DIR/bin/pip" install -r "$REQUIREMENTS"
fi

# Install systemd service
sudo cp "$SERVICE_FILE" /etc/systemd/system/sz_ui.service
sudo systemctl daemon-reload
sudo systemctl enable sz_ui.service
sudo systemctl restart sz_ui.service

echo "SentientZone setup complete."

