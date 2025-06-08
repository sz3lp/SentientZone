#!/bin/bash
# Automated deployment script for SentientZone using SSH keys or password auth

set -euo pipefail
# ensure required commands are available locally
for cmd in ssh git; do
    if ! command -v "$cmd" >/dev/null; then
        echo "$cmd command not found" >&2
        exit 1
    fi
done

SSH_CMD="ssh -o BatchMode=yes -o StrictHostKeyChecking=no"

else
    sudo git -C /opt/sentientzone pull --ff-only
usage() {
    echo "Usage: $0 -H <host> -U <user> -R <repo_url> [-p]" >&2
    echo "  -H  Raspberry Pi hostname or IP" >&2
    echo "  -U  SSH username" >&2
    echo "  -R  Git repository URL" >&2
    echo "  -p  Prompt for password instead of using SSH keys" >&2

set -euo pipefail

usage() {
    echo "Usage: $0 -H <host> -U <user> -R <repo_url>" >&2
    echo "  -H  Raspberry Pi hostname or IP" >&2
    echo "  -U  SSH username" >&2
    echo "  -R  Git repository URL" >&2
 main
}

PI_HOST=""
PI_USER=""
REPO_URL=""
 f8j5tt-codex/remove-plain-text-credentials-and-improve-config
USE_PASS=false

while getopts "H:U:R:p" opt; do


while getopts "H:U:R:" opt; do
 main
  case "$opt" in
    H) PI_HOST="$OPTARG" ;;
    U) PI_USER="$OPTARG" ;;
    R) REPO_URL="$OPTARG" ;;
 f8j5tt-codex/remove-plain-text-credentials-and-improve-config
    p) USE_PASS=true ;;

 main
    *) usage; exit 1 ;;
  esac
done

if [ -z "$PI_HOST" ] || [ -z "$PI_USER" ] || [ -z "$REPO_URL" ]; then
    usage
    exit 1
fi

 f8j5tt-codex/remove-plain-text-credentials-and-improve-config
SSH_CMD="ssh -o StrictHostKeyChecking=no"
if $USE_PASS; then
    if ! command -v sshpass >/dev/null; then
        echo "sshpass is required for password authentication. Please install it first." >&2
        exit 1
    fi
    read -s -p "Password for $PI_USER@$PI_HOST: " PI_PASS
    echo
    SSH_CMD="sshpass -p \"$PI_PASS\" ssh -o StrictHostKeyChecking=no"

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
 main
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
