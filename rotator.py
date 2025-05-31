# /sz/src/rotator.py

"""
Module: rotator.py
Purpose: Rotate and prune old log files for compliance and disk hygiene.
Consumes:
- CONFIG.log_dir
- CONFIG.retention_days
Produces:
- Keeps only logs newer than retention threshold
Behavior:
- Called once daily at midnight or system start
"""

import os
from datetime import datetime, timedelta
from config_loader import CONFIG

def rotate_logs():
    """
    Deletes log files older than CONFIG.retention_days.
    Targets CSV logs in log_dir.
    """
    cutoff = datetime.utcnow() - timedelta(days=CONFIG.retention_days)
    for filename in os.listdir(CONFIG.log_dir):
        if filename.endswith(".csv") or filename.startswith("daily_report_"):
            filepath = CONFIG.log_dir / filename
            try:
                ts_str = filename.split("_")[-1].replace(".csv", "").replace(".json", "").replace(".txt", "")
                file_date = datetime.strptime(ts_str, "%Y-%m-%d")
                if file_date < cutoff:
                    os.remove(filepath)
            except Exception:
                continue
