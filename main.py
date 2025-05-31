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
import sys # Added for graceful exit
import logging # Added for structured logging
from datetime import datetime # Added for precise time checks

# REMOVE THIS LINE: from config_loader import CONFIG
# ADD THIS IMPORT:
from state_manager import StateManager # Your new state manager

# --- GLOBAL APPLICATION SETUP ---
# It's good practice to set up basic logging as early as possible
# so all modules can use it.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
main_logger = logging.getLogger('MainApp') # A dedicated logger for main.py

# Instantiate the StateManager as the first thing that loads.
# It will automatically load config.json or create a default one.
app_state_manager = StateManager()

# Log initial system info using the state manager
controller_id = app_state_manager.get_value('controller_id', 'UNKNOWN')
main_logger.info(f"SentientZone Node (ID: {controller_id}) starting up.")
main_logger.info(f"Initial operating mode: {app_state_manager.get_value('current_mode')}")

# --- Import other modules (assuming they will be updated to accept app_state_manager) ---
# For now, these imports remain the same, but we will pass app_state_manager to their functions.
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
    All modules now receive the app_state_manager instance to access config and runtime state.
    """
    main_logger.info("[BOOT] Starting SentientZone main loop.")

    # Execute initial log rotation based on config
    # Pass the app_state_manager to rotator
    rotate_logs(app_state_manager)

    last_report_date = None # To track when the last daily report was generated

    while True:
        try:
            # Read sensors
            # Pass app_state_manager to read_sensors
            sensor_data = read_sensors(app_state_manager)

            # Get override mode
            # Pass app_state_manager to get_override_mode
            override_mode = get_override_mode(app_state_manager)

            # Decide HVAC action
            # Pass app_state_manager to decide_hvac_action
            decision = decide_hvac_action(sensor_data, override_mode, app_state_manager)

            # Log results
            # Pass app_state_manager to log_sensor_data and log_decision
            log_sensor_data(sensor_data, app_state_manager)
            log_decision(sensor_data, decision, app_state_manager)

            # Update watchdog
            # Pass app_state_manager to update_heartbeat
            update_heartbeat(app_state_manager)

            # Handle button press
            # Pass app_state_manager to detect_and_apply_override
            detect_and_apply_override(app_state_manager)

            # Daily report based on UTC hour from config
            now_utc = datetime.utcnow()
            report_hour = app_state_manager.get_value('report_hour_utc', 0) # Get from StateManager
            current_date_str = now_utc.strftime("%Y-%m-%d")

            # Check if it's the configured report hour and hasn't been reported for today yet
            if now_utc.hour == report_hour and current_date_str != last_report_date:
                main_logger.info(f"Generating daily report for {current_date_str} (UTC).")
                # Pass app_state_manager to generate_daily_report
                generate_daily_report(app_state_manager)
                last_report_date = current_date_str # Update last report date

            # Sleep for the configured sensor poll interval
            # Get interval from StateManager (using sensor_poll_interval_sec from DEFAULT_CONFIG)
            loop_interval = app_state_manager.get_value('sensor_poll_interval_sec', 30)
            time.sleep(loop_interval)

        except KeyboardInterrupt:
            main_logger.info("KeyboardInterrupt detected. Shutting down gracefully.")
            break # Exit the loop on Ctrl+C
        except Exception as e:
            # Use structured logging instead of print
            main_logger.error(f"An error occurred in main loop: {e}", exc_info=True)
            # Short sleep to prevent rapid error looping
            time.sleep(5)

# --- Application Entry Point ---
if __name__ == "__main__":
    try:
        main_loop()
    except Exception as final_e:
        # Catch any exceptions that escape the main_loop's inner try-except
        main_logger.critical(f"Unhandled exception during application runtime: {final_e}", exc_info=True)
    finally:
        # This block ensures cleanup happens whether there was an error or a graceful exit
        main_logger.info("Attempting to force save final configuration state...")
        # IMPORTANT: Force a save on application exit to ensure all pending changes are persisted
        app_state_manager.save_config_debounced(force=True)
        main_logger.info("Application shutdown complete.")
        sys.exit(0) # Explicitly exit with success status
