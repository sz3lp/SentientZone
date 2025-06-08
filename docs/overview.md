# System Overview

SentientZone runs entirely on a Raspberry Pi and does not require an internet connection. It
collects temperature and motion data and decides which HVAC mode to run.

## Architecture

```
[DHT22 + PIR] --> [SensorManager] --> [StateManager]
                                  \-> [MetricsManager]
[OverrideButton / API] --> [OverrideManager] --> [HVACController]
                                           \-> [StateManager]
                                 [Flask API]
                                    |
                                  Users
```

1. **SensorManager** reads temperature and motion every loop.
2. **OverrideManager** can force a mode for a set duration.
3. **HVACController** drives relays through the hardware interface.
4. **MetricsManager** records recent readings and errors.
5. **SentientZoneServer** exposes HTTP endpoints for monitoring and overrides.

The main loop in `main.py` ties these pieces together and handles shutdown signals.
