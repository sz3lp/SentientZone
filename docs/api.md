# API Reference

All POST requests require an `X-API-Key` header that matches the API key loaded
by `StateManager`. The value is taken from the `SZ_API_KEY` environment variable
or from the secrets file if provided. The server listens on `127.0.0.1:8080`.

## GET /state

Returns the full state stored by `StateManager`.

```
{
  "override_mode": "OFF",
  "override_until": null,
  "last_temp_f": 72.4,
  "last_motion_ts": 1685553912.0,
  "current_mode": "FAN_ONLY"
}
```

## POST /override

Apply a temporary override.

```
POST /override
Headers: X-API-Key: <key>
{
  "mode": "HEAT_ON",
  "duration_minutes": 30,
  "source": "api"
}
```

Responses:
- `200` with new override state
- `400` for invalid input
- `401` if the API key is missing or wrong

## GET /logs

Returns the current log file as plain text.

## GET /healthz

Reports service status. Returns `200` with JSON if healthy, otherwise `503`.

```
{
  "status": "ok",
  "uptime_sec": 1234,
  "mode": "FAN_ONLY",
  "last_temp_f": 72.5,
  "override_active": false,
  "errors": 0
}
```
