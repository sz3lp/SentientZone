#!/bin/bash
# Automated deployment script for SentientZone

PI_HOST="raspberrypi.local"
PI_USER="pi"
PI_PASS="raspberry"
REPO_URL="<REPLACE_WITH_YOUR_REPO>"

if ! command -v sshpass >/dev/null; then
  echo "sshpass is required. Please install it first." >&2
  exit 1
fi

sshpass -p "$PI_PASS" ssh -o StrictHostKeyChecking=no $PI_USER@$PI_HOST <<'EOF_REMOTE'
set -e

sudo apt-get update
sudo apt-get install -y git python3 python3-pip python3-flask
sudo pip3 install adafruit-circuitpython-dht RPi.GPIO

if [ ! -d /opt/sentientzone ]; then
    sudo git clone "$REPO_URL" /opt/sentientzone
fi

cd /opt/sentientzone
sudo cp sz_ui.service /etc/systemd/system/sz_ui.service
sudo systemctl daemon-reload
sudo systemctl enable sz_ui.service
sudo systemctl restart sz_ui.service
EOF_REMOTE

echo "Deployment complete."
