# /sz/src/main.py

"""
Module: main.py
Purpose: Primary runtime loop for SentientZone node.
Coordinates:
- Sensor reads
- Decision making
- Logging
- Override detection
- Watchdog update
- Button handling
"""

import time
from config_loader import CONFIG
from sensor_reader import read_sensors
from override_manager import get_override_mode
from decision_engine import decide_hvac_action
from logger import log_sensor_data, log_decision
from button import detect_and_apply_override
from watchdog import update_heartbeat
from rotator import rotate_logs
from report_generator import generate_daily_report

def main_loop():
    """
    Main control loop.
    """
    print("[BOOT] Starting SentientZone main loop")
    rotate_logs()
    last_report_date = None

    while True:
        try:
            # Read sensors
            sensor_data = read_sensors()
            override_mode = get_override_mode()
            decision = decide_hvac_action(sensor_data, override_mode)

            # Log results
            log_sensor_data(sensor_data)
            log_decision(sensor_data, decision)

            # Update watchdog
            update_heartbeat()

            # Handle button press
            detect_and_apply_override()

            # Daily report at 23:59 UTC
            now = time.gmtime()
            if now.tm_hour == 23 and now.tm_min == 59:
                current_date = time.strftime("%Y-%m-%d", now)
                if current_date != last_report_date:
                    generate_daily_report()
                    last_report_date = current_date

            time.sleep(CONFIG.loop_interval_sec)

        except Exception as e:
            print(f"[ERROR] {e}")
            time.sleep(5)

if __name__ == "__main__":
    main_loop()
