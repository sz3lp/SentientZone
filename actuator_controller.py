# /sz/src/actuator_controller.py

"""
Module: actuator_controller.py
Purpose: Apply HVAC state decisions to GPIO-controlled relays.
Consumes: hvac_state from decision_engine.py
Reads: CONFIG relay GPIO pins
Writes: GPIO pin values to control physical relays
Behavior:
- Only one HVAC mode active at a time
- Invalid state triggers full shutdown
"""

import digitalio
import board
from config_loader import CONFIG

# Setup relay pins
_relays = {
    "HEAT_ON": digitalio.DigitalInOut(board.D5),
    "COOL_ON": digitalio.DigitalInOut(board.D6),
    "HUMID_ON": digitalio.DigitalInOut(board.D13),
    "DEHUMID_ON": digitalio.DigitalInOut(board.D19)
}

for relay in _relays.values():
    relay.direction = digitalio.Direction.OUTPUT
    relay.value = False  # start in OFF state


def apply_hvac_state(hvac_state):
    """
    Set GPIO relays according to hvac_state.
    Valid states: HEAT_ON, COOL_ON, FAN_ONLY, OFF
    """
    _shutdown_all()

    if hvac_state == "HEAT_ON":
        _relays["HEAT_ON"].value = True
    elif hvac_state == "COOL_ON":
        _relays["COOL_ON"].value = True
    elif hvac_state == "FAN_ONLY":
        # No relay triggers, but placeholder for future integration
        pass
    elif hvac_state == "OFF":
        pass
    else:
        _shutdown_all()  # invalid state fallback


def _shutdown_all():
    for r in _relays.values():
        r.value = False
n