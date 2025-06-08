#!/bin/bash
# Automated deployment script for SentientZone using SSH keys

set -euo pipefail

usage() {
    echo "Usage: $0 -H <host> -U <user> -R <repo_url>" >&2
    echo "  -H  Raspberry Pi hostname or IP" >&2
    echo "  -U  SSH username" >&2
    echo "  -R  Git repository URL" >&2
}

PI_HOST=""
PI_USER=""
REPO_URL=""

while getopts "H:U:R:" opt; do
  case "$opt" in
    H) PI_HOST="$OPTARG" ;;
    U) PI_USER="$OPTARG" ;;
    R) REPO_URL="$OPTARG" ;;
    *) usage; exit 1 ;;
  esac
done

if [ -z "$PI_HOST" ] || [ -z "$PI_USER" ] || [ -z "$REPO_URL" ]; then
    usage
    exit 1
fi

if ! command -v ssh >/dev/null; then
    echo "ssh command not found" >&2
    exit 1
fi

if ! command -v git >/dev/null; then
    echo "git command not found" >&2
    exit 1
fi

SSH_CMD="ssh -o BatchMode=yes -o StrictHostKeyChecking=no"
if ! $SSH_CMD "$PI_USER@$PI_HOST" exit >/dev/null 2>&1; then
    echo "SSH connection failed. Ensure key-based authentication is configured." >&2
    exit 1
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
