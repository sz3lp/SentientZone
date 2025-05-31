# /sz/src/decision_engine.py

"""
Module: decision_engine.py
Purpose: Determine HVAC action based on sensor input, config, and override state.
Consumes:
- sensor_data from sensor_reader.read_sensors()
- override_mode: one of [AUTO, MANUAL_ON, MANUAL_OFF]
Provides:
- decide_hvac_action(sensor_data, override_mode) → dict with HVAC_STATE, mode, cause
This is a pure logic module: no GPIO, no I/O.
"""

from config_loader import CONFIG

# All valid output states
VALID_STATES = ["HEAT_ON", "COOL_ON", "FAN_ONLY", "OFF"]


def decide_hvac_action(sensor_data, override_mode):
    """
    Returns:
        dict: {
            'hvac_state': str,
            'mode': str,     # AUTO, MANUAL, FAILSAFE
            'cause': str     # HUMAN_OVERRIDE, SENSOR_FREEZE, TEMP_HIGH, etc.
        }
    """
    status = sensor_data["status"]
    motion = sensor_data["motion"]
    temp = sensor_data["temperature"]
    humid = sensor_data["humidity"]

    if override_mode == "manual_on":
        return _build("FAN_ONLY", "MANUAL", "HUMAN_OVERRIDE")

    if override_mode == "manual_off":
        return _build("OFF", "MANUAL", "HUMAN_OVERRIDE")

    if status in ["ERROR", "FROZEN"]:
        return _build("OFF", "FAILSAFE", f"SENSOR_{status}")

    if motion:
        if temp < CONFIG.temp_min_comfort:
            return _build("HEAT_ON", "AUTO", "TEMP_LOW")
        elif temp > CONFIG.temp_max_comfort:
            return _build("COOL_ON", "AUTO", "TEMP_HIGH")
        else:
            return _build("OFF", "AUTO", "COMFORT_RANGE")

    # No motion → relax to off unless humidity critical
    if humid is not None:
        if humid < CONFIG.humid_min_comfort:
            return _build("FAN_ONLY", "AUTO", "DRY_IDLE")
        elif humid > CONFIG.humid_max_comfort:
            return _build("FAN_ONLY", "AUTO", "HUMID_IDLE")

    return _build("OFF", "AUTO", "UNOCCUPIED")


def _build(state, mode, cause):
    return {
        "hvac_state": state,
        "mode": mode,
        "cause": cause
    }
