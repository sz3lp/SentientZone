# /sz/src/heartbeat_writer.py

"""
Module: heartbeat_writer.py
Purpose: Periodically record system liveness with full identity stamp.
Consumes:
- CONFIG.heartbeat_file
- CONFIG.zone_id, room_name, building, climate_zone
Produces:
- /sz/status/heartbeat.txt with UTC timestamp + identity
Behavior:
- Used by human technicians or automated cron to verify node is live
- Format is deterministic, line-based, machine-readable
"""

from datetime import datetime
from config_loader import CONFIG


def write_heartbeat():
    """
    Write zone identity and timestamp to heartbeat file.
    Format:
        <UTC_ISO_TIMESTAMP> | <ZONE_ID> | <BUILDING> | <ROOM>
    """
    line = f"{datetime.utcnow().isoformat()} | {CONFIG.zone_id} | {CONFIG.building} | {CONFIG.room_name}\n"
    try:
        CONFIG.heartbeat_file.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG.heartbeat_file, "w") as f:
            f.write(line)
    except Exception:
        pass  # Silent fail; watchdog handles absence
