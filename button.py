# /sz/src/button.py

"""
Module: button.py
Purpose: Detect physical button press and apply local override.
Consumes:
- GPIO input pin
- CONFIG.override_file
Provides:
- detect_and_apply_override(): triggers override mode toggle
Behavior:
- On button press, toggles between "manual_on" and "manual_off"
- Skips debounce and long-press handling for MVP
"""

import board
import digitalio
import time
from config_loader import CONFIG

# Button setup (assume pulled high, active low)
button = digitalio.DigitalInOut(board.D26)
button.direction = digitalio.Direction.INPUT
button.pull = digitalio.Pull.UP

# Internal toggle tracker
_last_state = "manual_off"

def detect_and_apply_override():
    """
    Polls button input and writes override toggle if pressed.
    Should be called once per main loop cycle.
    """
    global _last_state

    if not button.value:  # Button pressed (active low)
        new_state = "manual_on" if _last_state == "manual_off" else "manual_off"
        try:
            with open(CONFIG.override_file, "w") as f:
                f.write(new_state)
            _last_state = new_state
            time.sleep(0.3)  # debounce delay
        except Exception:
            pass
