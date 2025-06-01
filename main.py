# /sz/src/main.py

import time
import logging
import sys
import threading
import signal

# Import core modules
from state_manager import StateManager
from logger import setup_logging
import sensor_reader
import decision_engine
import actuator_control
import watchdog
import button
import rotator
import report_generator

# --- Global Variables ---
app_state_manager: StateManager = None
main_logger: logging.Logger = None
running_event = threading.Event() # Event to signal threads to stop gracefully

# --- Signal Handler for Graceful Shutdown ---
def signal_handler(sig, frame):
    global main_logger
    if main_logger:
        main_logger.info(f"Received signal {sig}. Initiating graceful shutdown...")
    else:
        print(f"Received signal {sig}. Initiating graceful shutdown...")
    
    running_event.set() # Set the event to signal threads to stop
    sys.exit(0) # Exit the main process

# Register signal handlers for graceful shutdown (e.g., Ctrl+C, systemd stop)
signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
signal.signal(signal.SIGTERM, signal_handler) # Systemd stop command

# --- Main Application Logic ---
def main():
    global app_state_manager, main_logger

    try:
        # 1. Setup Logging
        log_file = '/sz/logs/sentientzone.log'
        setup_logging(log_file)
        main_logger = logging.getLogger('MainApp')
        main_logger.info("SentientZone application starting...")

        # 2. Initialize StateManager
        config_file = '/sz/config/config.json'
        app_state_manager = StateManager(config_file)
        main_logger.info("StateManager initialized. Configuration loaded.")

        # 3. Initialize Actuator Control
        # This will configure GPIOs for controlling HVAC relays
        if not actuator_control.setup_actuators(app_state_manager):
            main_logger.critical("Failed to setup HVAC actuators. Exiting.")
            running_event.set() # Signal immediate shutdown
            return
        main_logger.info("HVAC Actuator Control initialized.")

        # 4. Initialize Sensor Reader
        # This will set up the connection for reading temp/humidity sensors
        # This needs to be able to handle both wired and wireless sensors (via MQTT)
        if not sensor_reader.setup_sensors(app_state_manager, running_event):
            main_logger.critical("Failed to setup sensor reader. Exiting.")
            running_event.set() # Signal immediate shutdown
            return
        main_logger.info("Sensor Reader initialized.")

        # 5. Initialize Watchdog
        # This ensures the system self-restarts if the main loop hangs
        watchdog_timeout_seconds = app_state_manager.get_value('watchdog_timeout_seconds', 300)
        watchdog_period_seconds = app_state_manager.get_value('watchdog_period_seconds', 60)
        watchdog.setup_watchdog(watchdog_timeout_seconds, watchdog_period_seconds)
        main_logger.info(f"Watchdog initialized with timeout {watchdog_timeout_seconds}s and period {watchdog_period_seconds}s.")
        watchdog.signal() # Initial signal to the watchdog

        # 6. Initialize User Input Devices (Button and Rotary Encoder)
        # These will run in separate threads to not block the main loop
        if app_state_manager.get_value('button_enabled', False):
            if not button.setup_button(app_state_manager, running_event):
                 main_logger.warning("Failed to setup button input. Continuing without button.")
            else:
                main_logger.info("Button input initialized.")
        
        if app_state_manager.get_value('rotator_enabled', False):
            if not rotator.setup_rotator(app_state_manager, running_event):
                 main_logger.warning("Failed to setup rotary encoder. Continuing without rotator.")
            else:
                main_logger.info("Rotary encoder initialized.")

        main_logger.info("All components initialized. Starting main loop...")

        # --- Main Application Loop ---
        loop_interval_seconds = app_state_manager.get_value('main_loop_interval_seconds', 10)
        report_interval_minutes = app_state_manager.get_value('report_interval_minutes', 60)
        last_report_time = time.time() # Track last report generation time

        while not running_event.is_set(): # Loop until shutdown signal is received
            start_loop_time = time.time()
            main_logger.debug("Main loop iteration started.")

            # 7. Read Sensor Data
            # Sensor data is read by sensor_reader's internal loop (if wireless)
            # or directly here (if wired, or just retrieve latest from internal buffer)
            current_sensor_data = sensor_reader.get_latest_sensor_data(app_state_manager)
            app_state_manager.set_value('current_sensor_data', current_sensor_data)
            main_logger.debug(f"Latest sensor data: {current_sensor_data}")

            # 8. Get HVAC Feedback (from actuator_control)
            hvac_feedback = actuator_control.get_hvac_feedback()
            app_state_manager.set_value('hvac_line_status', hvac_feedback)
            main_logger.debug(f"HVAC line feedback: {hvac_feedback}")

            # 9. Make Decision
            # The decision engine uses sensor data, setpoints, current state from StateManager
            desired_mode, desired_fan_state = decision_engine.make_decision(app_state_manager)
            main_logger.debug(f"Decision: Mode={desired_mode}, Fan={desired_fan_state}")

            # 10. Actuate HVAC
            # Only send command if it's different from the currently commanded state
            current_hvac_mode = app_state_manager.get_value('current_hvac_mode', 'OFF')
            current_fan_state = app_state_manager.get_value('current_fan_state', 'AUTO')

            if desired_mode != current_hvac_mode or desired_fan_state != current_fan_state:
                actuator_control.set_hvac_state(desired_mode, desired_fan_state, app_state_manager)
                main_logger.info(f"HVAC state changed to Mode: {desired_mode}, Fan: {desired_fan_state}")
            else:
                main_logger.debug("HVAC state unchanged.")

            # 11. Generate Periodic Reports
            if (time.time() - last_report_time) >= (report_interval_minutes * 60):
                report_generator.generate_report(app_state_manager)
                last_report_time = time.time()
                main_logger.info("Generated periodic system report.")

            # 12. Signal Watchdog
            watchdog.signal()
            main_logger.debug("Watchdog signaled.")

            # 13. Maintain Loop Interval
            elapsed_time = time.time() - start_loop_time
            sleep_time = loop_interval_seconds - elapsed_time
            if sleep_time > 0:
                time.sleep(sleep_time)
            else:
                main_logger.warning(f"Main loop took too long ({elapsed_time:.2f}s). No sleep this iteration.")

    except Exception as e:
        if main_logger:
            main_logger.critical(f"An unhandled error occurred in main loop: {e}", exc_info=True)
        else:
            print(f"An unhandled error occurred before logger was fully initialized: {e}")
            import traceback
            traceback.print_exc()

    finally:
        # --- Graceful Shutdown ---
        if main_logger:
            main_logger.info("Initiating final cleanup and shutdown procedures...")
        else:
            print("Initiating final cleanup and shutdown procedures...")

        # Signal all threads to stop
        running_event.set()

        # Stop and cleanup user input devices
        if app_state_manager and app_state_manager.get_value('button_enabled', False):
            button.cleanup_button()
        if app_state_manager and app_state_manager.get_value('rotator_enabled', False):
            rotator.cleanup_rotator()

        # Cleanup actuator GPIOs (ensure HVAC is off)
        actuator_control.cleanup_actuators()

        # Cleanup sensor reader (e.g., MQTT client disconnect)
        if app_state_manager and app_state_manager.get_value('sensor_reader_type', 'wired') == 'mqtt':
            sensor_reader.disconnect_mqtt_client()
        
        # Save final state
        if app_state_manager:
            app_state_manager.save_config_debounced(force=True)
            report_generator.generate_report(app_state_manager, final_report=True) # Generate final report
            main_logger.info("Final state saved and report generated.")
        
        if main_logger:
            main_logger.info("SentientZone application gracefully shut down.")
        else:
            print("SentientZone application gracefully shut down.")

if __name__ == '__main__':
    main()
