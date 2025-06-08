# Configuration

All runtime settings are stored in `config/config.json`. The file is loaded by
`StateManager` at startup. The API key value in this file should be set to a
placeholder such as `CHANGE_ME`. The real key is loaded at runtime from the
`SZ_API_KEY` environment variable or from a secrets file.

## Schema

- `pins.dht` – GPIO for the DHT22 sensor
- `pins.motion` – GPIO for the PIR motion sensor
- `pins.cooling` – GPIO controlling the cooling relay
- `pins.heating` – GPIO controlling the heating relay
- `pins.fan` – GPIO controlling the fan relay
- `pins.button` – GPIO for the optional override button
- `thresholds.cool` – temperature in °F above which cooling activates
- `thresholds.heat` – temperature in °F below which heating activates
- `loop_interval` – seconds between control loop iterations
- `motion_timeout` – seconds after last motion allowed for cooling
- `api_key` – key required for POST requests

## Example

```json
{
  "pins": {
    "dht": 17,
    "motion": 27,
    "cooling": 23,
    "heating": 22,
    "fan": 24,
    "button": 6
  },
  "thresholds": {
    "cool": 75,
    "heat": 68
  },
  "loop_interval": 5,
  "motion_timeout": 300,
  "api_key": "CHANGE_ME"
}
```

### Guidelines

- Modify the file only when the service is stopped to avoid race conditions.
- Keep a backup of the original configuration.
- Store your real API key in the `SZ_API_KEY` environment variable or a file
  specified by `SZ_API_KEY_FILE` (defaults to `config/api_key.secret`). Never
  commit the secrets file to version control.
