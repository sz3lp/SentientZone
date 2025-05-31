# /sz/src/watchdog.py

"""
Module: watchdog.py
Purpose: Monitor system health and trigger reboot if unresponsive.
Consumes:
- Periodic ping from main loop
- CONFIG.heartbeat_file path
Behavior:
- Updates heartbeat file with current UTC timestamp
- External systemd Watchdog or cron monitors file age
"""

from datetime import datetime
from config_loader import CONFIG

def update_heartbeat():
    """
    Writes current UTC timestamp to heartbeat file.
    This signals system is alive.
    """
    timestamp = datetime.utcnow().isoformat()
    try:
        CONFIG.heartbeat_file.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG.heartbeat_file, "w") as f:
            f.write(timestamp)
    except Exception as e:
        # In a hardened system, this would log to a secondary error channel
        pass
