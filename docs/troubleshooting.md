# Troubleshooting

This guide covers common issues seen when deploying SentientZone.

## Sensor Read Failures

- Ensure the DHT22 and PIR sensors are wired correctly.
- Check that the pins in `config/config.json` match your wiring.
- Look for errors in `/home/pi/sz/logs/sentientzone.log`.

## Permission Denied on GPIO

- The service must run with permissions to access `/dev/gpiomem`.
- Running via the provided `sz_ui.service` unit grants the required access.

## Service Will Not Start

- Inspect the service logs with `sudo journalctl -u sz_ui.service`.
- Verify Python dependencies are installed in `/home/pi/sz/venv`.
- Confirm that `state/` and `logs/` directories exist and are writable.

## Logs Missing or Not Rotating

- Check file permissions on `/home/pi/sz/logs`.
- The logger rotates files daily and keeps 7 backups.
- If the directory is on a read-only filesystem, logging will fail.

## Resetting State Safely

If the state file becomes corrupted you can reset it:

```bash
sudo systemctl stop sz_ui.service
rm -f /home/pi/sz/state/state.json
cp /home/pi/sz/state/state_backup.json /home/pi/sz/state/state.json
sudo systemctl start sz_ui.service
```
