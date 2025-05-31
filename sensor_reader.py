# /sz/src/sensor_reader.py

"""
Module: sensor_reader.py
Purpose: Collect temperature, humidity, and motion data from GPIO sensors.
Consumes: CONFIG object from config_loader.py
Provides: read_sensors() → dict with values and status
Behavior:
- Validates readings for plausibility
- Maintains rolling history to detect frozen sensor states
- Marks data as VALID, STALE, FROZEN, or ERROR
- Assumes DHT22 on board.D17 and PIR on board.D22 (as per config)
"""

import board
import adafruit_dht
import digitalio
import time
from collections import deque
from config_loader import CONFIG

# Sensor setup
_dht = adafruit_dht.DHT22(board.D17)
_pir = digitalio.DigitalInOut(board.D22)
_pir.direction = digitalio.Direction.INPUT

# Rolling buffer for freeze detection
_buffer_size = CONFIG.freeze_sensor_window // CONFIG.sensor_interval_sec
_temp_history = deque(maxlen=_buffer_size)
_humid_history = deque(maxlen=_buffer_size)


def _is_frozen(history, current_value):
    """Check if sensor value is frozen (same for entire window)."""
    if len(history) < history.maxlen:
        return False
    return all(abs(v - current_value) < 0.1 for v in history)


def read_sensors():
    """Read all sensors and return structured result with status."""
    try:
        temp = _dht.temperature
        humid = _dht.humidity
        motion = _pir.value

        if temp is None or humid is None:
            return _build_result("ERROR", None, None, motion)

        if not (-40 <= temp <= 80 and 0 <= humid <= 100):
            return _build_result("STALE", temp, humid, motion)

        # Check for freeze
        frozen = _is_frozen(_temp_history, temp) and _is_frozen(_humid_history, humid)

        # Update history
        _temp_history.append(temp)
        _humid_history.append(humid)

        status = "FROZEN" if frozen else "VALID"
        return _build_result(status, temp, humid, motion)

    except Exception as e:
        return _build_result("ERROR", None, None, None, str(e))


def _build_result(status, temp, humid, motion, error=None):
    return {
        "status": status,
        "temperature": temp,
        "humidity": humid,
        "motion": bool(motion) if motion is not None else False,
        "timestamp": time.time(),
        "error": error if error else ""
    }
