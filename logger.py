# /sz/src/logger.py

"""
Module: logger.py
Purpose: Log sensor readings and decisions to CSV for audit and analysis.
Consumes:
- sensor_data (dict)
- hvac_decision (dict)
- StateManager for log file paths.
Produces:
- Configurable data.csv and decisions.csv files.
- Logs structured rows with timestamp, temp, humid, motion, state, mode, cause.
"""

import csv
import os
import pathlib # For handling file paths as Path objects
from datetime import datetime
import logging # For logging internal module events/errors

# REMOVE THIS LINE: from config_loader import CONFIG
# ADD THIS IMPORT:
from state_manager import StateManager

# Setup module-specific logger for internal errors/info about logging operations
logger_module_logger = logging.getLogger('LoggerModule')

# Define headers for CSV files
DATA_LOG_HEADERS = ["timestamp", "temperature", "humidity", "motion", "status"]
DECISION_LOG_HEADERS = ["timestamp", "temperature", "humidity", "motion", "hvac_state", "mode", "cause"]


def log_sensor_data(sensor_data: dict, state_manager: StateManager):
    """
    Append temperature, humidity, motion, and status to the sensor data CSV.

    Args:
        sensor_data (dict): Dictionary containing sensor readings.
        state_manager (StateManager): The application's state manager instance.
    """
    # Get the log directory and filename from StateManager
    log_dir_str = state_manager.get_value('log_directory', '/var/log/sentientzone')
    data_log_filename = state_manager.get_value('sensor_log_file', 'data.csv')
    
    # Construct the full path using pathlib for robust path handling
    data_log_path = pathlib.Path(log_dir_str) / data_log_filename

    row = [
        _timestamp(),
        sensor_data.get("temperature"), # Use .get() to safely access keys
        sensor_data.get("humidity"),
        int(sensor_data.get("motion", False)), # Default to False if missing, convert to int
        sensor_data.get("status")
    ]
    _write_row(data_log_path, DATA_LOG_HEADERS, row)
    logger_module_logger.debug(f"Logged sensor data: {row}")


def log_decision(sensor_data: dict, decision: dict, state_manager: StateManager):
    """
    Append HVAC decision result to the decisions CSV including cause and mode.

    Args:
        sensor_data (dict): Dictionary containing sensor readings at time of decision.
        decision (dict): Dictionary containing the HVAC decision.
        state_manager (StateManager): The application's state manager instance.
    """
    # Get the log directory and filename from StateManager
    log_dir_str = state_manager.get_value('log_directory', '/var/log/sentientzone')
    decision_log_filename = state_manager.get_value('hvac_log_file', 'decisions.csv')
    
    # Construct the full path using pathlib
    decision_log_path = pathlib.Path(log_dir_str) / decision_log_filename

    row = [
        _timestamp(),
        sensor_data.get("temperature"),
        sensor_data.get("humidity"),
        int(sensor_data.get("motion", False)),
        decision.get("hvac_state"),
        decision.get("mode"),
        decision.get("cause")
    ]
    _write_row(decision_log_path, DECISION_LOG_HEADERS, row)
    logger_module_logger.debug(f"Logged HVAC decision: {row}")


def _write_row(path: pathlib.Path, headers: list, row: list):
    """
    Helper function to write a single row to a CSV file.
    Ensures directory exists and writes headers if the file is new.
    """
    try:
        # Ensure the parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        file_exists = path.exists() # Check if file exists BEFORE opening in append mode

        with open(path, "a", newline="") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(headers) # Write headers only if file is new
                logger_module_logger.info(f"Created new log file and wrote headers: {path}")
            writer.writerow(row)
    except IOError as e:
        logger_module_logger.error(f"Failed to write to log file '{path}': {e}")
    except Exception as e:
        logger_module_logger.critical(f"An unexpected error occurred while writing to '{path}': {e}", exc_info=True)


def _timestamp() -> str:
    """Returns the current UTC timestamp in ISO 8601 format."""
    return datetime.utcnow().isoformat()


# Example Usage for Testing (remove for main integration)
if __name__ == '__main__':
    class MockStateManager:
        def __init__(self):
            # Define mock config values for log files and directory
            self._config = {
                'log_directory': './test_logs',
                'sensor_log_file': 'test_data.csv',
                'hvac_log_file': 'test_decisions.csv'
            }
            # Set up basic logging for the mock environment
            logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            logger_module_logger.setLevel(logging.DEBUG)

            # Clean up old test log files and directory
            if os.path.exists(self._config['log_directory']):
                import shutil
                shutil.rmtree(self._config['log_directory']) # Remove directory and its contents
            os.makedirs(self._config['log_directory'])
            logger_module_logger.info(f"Cleaned and created test log directory: {self._config['log_directory']}")


        def get_value(self, key, default=None):
            return self._config.get(key, default)

        def set_value(self, key, value, bypass_validation=False):
            self._config[key] = value
            logger_module_logger.debug(f"MockStateManager: Set '{key}' to '{value}'")

    print("--- Testing logger.py independently ---")
    mock_sm = MockStateManager()

    test_sensor_data_1 = {
        'temperature': 22.1,
        'humidity': 45.2,
        'motion': True,
        'status': 'VALID'
    }
    test_decision_1 = {
        'hvac_state': 'OFF',
        'mode': 'AUTO',
        'cause': 'COMFORT_RANGE'
    }

    test_sensor_data_2 = {
        'temperature': 19.5,
        'humidity': 40.0,
        'motion': True,
        'status': 'VALID'
    }
    test_decision_2 = {
        'hvac_state': 'HEAT_ON',
        'mode': 'AUTO',
        'cause': 'TEMP_LOW'
    }

    print("\n--- Logging first set of data ---")
    log_sensor_data(test_sensor_data_1, mock_sm)
    log_decision(test_sensor_data_1, test_decision_1, mock_sm)

    print("\n--- Logging second set of data ---")
    log_sensor_data(test_sensor_data_2, mock_sm)
    log_decision(test_sensor_data_2, test_decision_2, mock_sm)

    # Verify content of the test files
    sensor_log_path = pathlib.Path(mock_sm.get_value('log_directory')) / mock_sm.get_value('sensor_log_file')
    hvac_log_path = pathlib.Path(mock_sm.get_value('log_directory')) / mock_sm.get_value('hvac_log_file')

    print(f"\nContents of {sensor_log_path}:")
    with open(sensor_log_path, 'r') as f:
        print(f.read())
    
    print(f"\nContents of {hvac_log_path}:")
    with open(hvac_log_path, 'r') as f:
        print(f.read())

    # Clean up test log files and directory after testing
    import shutil
    if os.path.exists(mock_sm.get_value('log_directory')):
        shutil.rmtree(mock_sm.get_value('log_directory'))

    print("\nLogger tests complete.")
