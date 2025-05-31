# /sz/src/logger.py

"""
Module: logger.py
Purpose: Log sensor readings and decisions to CSV for audit and analysis.
Consumes: sensor_data, hvac_decision
Produces:
- /sz/logs/data.csv
- /sz/logs/decisions.csv
- Logs structured rows with timestamp, temp, humid, motion, state, mode, cause
"""

import csv
import os
from datetime import datetime
from config_loader import CONFIG

DATA_LOG = CONFIG.log_dir / "data.csv"
DECISION_LOG = CONFIG.log_dir / "decisions.csv"


def log_sensor_data(sensor_data):
    """
    Append temperature, humidity, motion, and status to data.csv.
    """
    row = [
        _timestamp(),
        sensor_data["temperature"],
        sensor_data["humidity"],
        int(sensor_data["motion"]),
        sensor_data["status"]
    ]
    _write_row(DATA_LOG, row)


def log_decision(sensor_data, decision):
    """
    Append decision result to decisions.csv including cause and mode.
    """
    row = [
        _timestamp(),
        sensor_data["temperature"],
        sensor_data["humidity"],
        int(sensor_data["motion"]),
        decision["hvac_state"],
        decision["mode"],
        decision["cause"]
    ]
    _write_row(DECISION_LOG, row)


def _write_row(path, row):
    os.makedirs(path.parent, exist_ok=True)
    with open(path, "a", newline="") as f:
        csv.writer(f).writerow(row)


def _timestamp():
    return datetime.utcnow().isoformat()
