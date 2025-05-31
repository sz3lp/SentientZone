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
- HVAC Actuation (Implicit via decision -> actuator)
"""

import time
import sys
import logging
from datetime import datetime

# Import the new StateManager
from state_manager import StateManager

# Import the refactored SensorManager class
from sensor_reader import SensorManager

# Import the refactored button functions
from button import setup_button, detect_and_apply_override, cleanup_button

# --- GLOBAL APPLICATION SETUP ---
# Configure basic logging early. This ensures all modules can use it.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
main_logger = logging.getLogger('MainApp') # A dedicated logger for main.py

# 1. Instantiate the StateManager. This is the central source of truth.
# It will automatically load config.json or create a default one.
app_state_manager = StateManager()

# Log initial system info using the state manager
controller_id = app_state_manager.get_value('controller_id', 'UNKNOWN')
main_logger.info(f"SentientZone Node (ID: {controller_id}) starting up.")
main_logger.info(f"Initial operating mode: {app_state_manager.get_value('current_mode')}")

# 2. Instantiate SensorManager, passing the app_state_manager
# This sets up the physical sensor connections once at startup.
sensor_manager_instance = SensorManager(app_state_manager)

# 3. Initialize Button hardware
# This sets up the physical button input once at startup.
setup_button(app_state_manager)

# --- Import other modules (will be updated to accept app_state_manager) ---
# These imports remain, but their functions will be called with the state_manager instance.
from override_manager import get_override_mode
from decision_engine import decide_hvac_action
from logger import log_sensor_data, log_decision
from watchdog import update_heartbeat
from rotator import rotate_logs
from report_generator import generate_daily_report

# --- Main Application Loop ---
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
            # Read sensors using the instantiated SensorManager
            sensor_data = sensor_manager_instance.read_sensors()

            # Get override mode
            override_mode = get_override_mode(app_state_manager)

            # Decide HVAC action
            decision = decide_hvac_action(sensor_data, override_mode, app_state_manager)

            # Log results
            log_sensor_data(sensor_data, app_state_manager)
            log_decision(sensor_data, decision, app_state_manager)

            # Update watchdog
            update_heartbeat(app_state_manager)

            # Handle button press
            detect_and_apply_override(app_state_manager)

            # Daily report based on UTC hour from config
            now_utc = datetime.utcnow()
            report_hour = app_state_manager.get_value('report_hour_utc', 0) # Get from StateManager
            current_date_str = now_utc.strftime("%Y-%m-%d")

            # Check if it's the configured report hour and hasn't been reported for today yet
            if now_utc.hour == report_hour and current_date_str != last_report_date:
                main_logger.info(f"Generating daily report for {current_date_str} (UTC).")
                generate_daily_report(app_state_manager)
                last_report_date = current_date_str # Update last report date

            # Sleep for the configured sensor poll interval
            loop_interval = app_state_manager.get_value('sensor_poll_interval_sec', 30)
            time.sleep(loop_interval)

        except KeyboardInterrupt:
            main_logger.info("KeyboardInterrupt detected. Shutting down gracefully.")
            break # Exit the loop on Ctrl+C
        except Exception as e:
            main_logger.error(f"An error occurred in main loop: {e}", exc_info=True)
            time.sleep(5) # Short sleep to prevent rapid error looping

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
        
        # Clean up SensorManager resources (GPIO)
        if 'sensor_manager_instance' in locals() and sensor_manager_instance:
            sensor_manager_instance.cleanup()

        # Clean up Button GPIO resources
        # The 'cleanup_button()' function is called directly as it's a global function
        # and doesn't rely on an instantiated object being present in 'locals()'
        cleanup_button()

        main_logger.info("Application shutdown complete.")
        sys.exit(0) # Explicitly exit with success status
