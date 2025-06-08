# SentientZone

SentientZone is an offline HVAC controller built for Raspberry Pi. It reads a DHT22
sensor and PIR motion detector, then actuates cooling, heating and fan relays based
on configurable thresholds. A small Flask API exposes the current state, allows
manual overrides, and serves log files.

## Hardware Requirements

- Raspberry Pi 4 (or compatible)
- DHT22 temperature/humidity sensor
- PIR motion sensor
- Three relay channels for cooling, heating and fan
- Optional button for local override

## Software Overview

The system is organised into modules:

- **sensors.py** – reads temperature and motion
- **control.py** – drives relays via the hardware interface
- **hardware.py** – abstracts GPIO operations
- **state_manager.py** – persists state to `state/state.json`
- **override_handler.py** – manages timed overrides
- **server.py** – Flask API exposing `/state`, `/override`, `/logs` and `/healthz`
- **metrics.py** – writes runtime metrics to `logs/metrics.json`
- **main.py** – entry point coordinating the control loop and background threads

Daily logs are written to `$SZ_BASE_DIR/logs/sentientzone.log` by default.

## Quickstart

```bash
# Clone repository
git clone <REPO_URL>
cd SentientZone

# Install system and Python dependencies
./setup.sh

# Provide your API key securely
export SZ_API_KEY=<your-key>
# or place it in config/api_key.secret (do not commit this file)

# Start application (systemd unit installs as sz_ui.service)
sudo systemctl start sz_ui.service
```

The installer assumes the project will be placed in `/home/pi/sz` and will run
under the `pi` user.  To override these defaults set the environment variables
`SZ_BASE_DIR` and `SZ_USER` before running `setup.sh`:

```bash
export SZ_BASE_DIR=/opt/sz
export SZ_USER=ubuntu
./setup.sh
```
These variables are also read by `sz_ui.service`, `logger.py` and
`metrics.py`, so the service will start correctly even if the repository lives
outside `/home/pi`.

## Environment Variables

| Variable      | Description                                     | Default          |
|---------------|-------------------------------------------------|------------------|
| `SZ_BASE_DIR` | Base directory for the repository and runtime.  | `/home/pi/sz`    |
| `SZ_USER`     | Linux user the systemd service runs under.      | `pi`             |

During development you can run the program manually:

```bash
python main.py
```

## Deploy to Raspberry Pi

 f8j5tt-codex/remove-plain-text-credentials-and-improve-config
Use the `deploy_to_pi.sh` script to install or update SentientZone on your Pi:

```bash
./deploy_to_pi.sh -H <pi_host> -U <pi_user> -R <repo_url> [-p]
```

Provide `-p` to be prompted for the SSH password, otherwise the script assumes
key-based authentication.

The `deploy_to_pi.sh` script installs or updates SentientZone on a Raspberry Pi
configured for key-based SSH access:

```bash
./deploy_to_pi.sh -H <pi_host> -U <pi_user> -R <repo_url>
```

The repository is cloned to `/opt/sentientzone` and the service started using
`sz_ui.service`. The script fails if an SSH connection cannot be established.

 main

## Directory Structure

```
config/           Configuration files
state/            Persistent runtime state
logs/             Log and metrics output
tests/            Pytest suite and mocks
.github/workflows CI configuration
```

See the `docs/` directory for API details, configuration reference and troubleshooting.

## Maintainer & License

Maintained by the SentientZone team. Released under the MIT License. See
[LICENSE](LICENSE) for details.
