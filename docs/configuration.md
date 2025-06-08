# Configuration

All runtime settings are stored in `config/config.json`. The file is loaded by
`StateManager` at startup.

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
    "dht": 4,
    "motion": 5,
    "cooling": 17,
    "heating": 27,
    "fan": 22,
    "button": 6
  },
  "thresholds": {
    "cool": 75,
    "heat": 68
  },
  "loop_interval": 5,
  "motion_timeout": 300,
  "api_key": "mysecret"
}
```

### Guidelines

- Modify the file only when the service is stopped to avoid race conditions.
- Keep a backup of the original configuration.
- Ensure the API key is kept secret if the network is exposed.
