# /sz/src/override_manager.py

"""
Module: override_manager.py
Purpose: Determine current override mode from local file and schedule.
Consumes:
- /sz/control/override.txt (user-triggered)
- /sz/config/override_schedule.json (predefined schedule)
- CONFIG.default_mode as fallback
Produces:
- override_mode: one of ["auto", "manual_on", "manual_off"]
Behavior:
- Fallback to CONFIG.default_mode if all inputs fail
- Manual file-based override takes priority
- Schedule only applies if file is absent or empty
"""

import json
from datetime import datetime
from config_loader import CONFIG


def get_override_mode():
    """
    Returns:
        str: override_mode ("auto", "manual_on", "manual_off")
    """
    override_path = CONFIG.override_file

    # Manual override file priority
    if override_path.exists():
        try:
            mode = override_path.read_text().strip().lower()
            if mode in ("auto", "manual_on", "manual_off"):
                return mode
        except Exception:
            pass  # ignore malformed input

    # Schedule fallback
    try:
        with open(CONFIG.schedule_file, "r") as f:
            schedule = json.load(f)
            now = datetime.now()
            current_hour = now.hour
            current_weekday = now.weekday()  # 0 = Monday
            for rule in schedule.get("rules", []):
                if rule["weekday"] == current_weekday and rule["hour"] == current_hour:
                    return rule["mode"]
    except Exception:
        pass  # ignore schedule errors

    # Final fallback
    return CONFIG.default_mode
