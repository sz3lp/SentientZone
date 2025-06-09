#!/bin/bash
# Automated deployment script for SentientZone

set -e

usage() {
    echo "Usage: $0 -H <host> -U <user> -R <repo_url> [-p]" >&2
    echo "  -H  Raspberry Pi hostname or IP" >&2
    echo "  -U  SSH username" >&2
    echo "  -R  Git repository URL" >&2
    echo "  -p  Prompt for password instead of using SSH keys" >&2
}

PI_HOST=""
PI_USER=""
REPO_URL=""
USE_PASS=false

while getopts "H:U:R:p" opt; do
  case "$opt" in
    H) PI_HOST="$OPTARG" ;;
    U) PI_USER="$OPTARG" ;;
    R) REPO_URL="$OPTARG" ;;
    p) USE_PASS=true ;;
    *) usage; exit 1 ;;
  esac
done

if [ -z "$PI_HOST" ] || [ -z "$PI_USER" ] || [ -z "$REPO_URL" ]; then
    usage
    exit 1
fi

SSH_CMD="ssh -o StrictHostKeyChecking=no"
if $USE_PASS; then
    if ! command -v sshpass >/dev/null; then
        echo "sshpass is required for password authentication. Please install it first." >&2
        exit 1
    fi
    read -s -p "Password for $PI_USER@$PI_HOST: " PI_PASS
    echo
    SSH_CMD="sshpass -p \"$PI_PASS\" ssh -o StrictHostKeyChecking=no"
fi

$SSH_CMD $PI_USER@$PI_HOST <<EOF_REMOTE
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
