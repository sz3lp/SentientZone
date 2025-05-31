# /sz/src/override_manager.py

"""
Module: override_manager.py
Purpose: Determine current override mode from local file and schedule.
Consumes:
- StateManager for paths (override.txt, schedule.json) and default mode.
Produces:
- override_mode: one of ["auto", "manual_on", "manual_off"]
Behavior:
- Fallback to StateManager.default_mode if all inputs fail.
- Manual file-based override takes priority.
- Schedule only applies if manual override file is absent or invalid.
"""

import json
import os # To check for file existence
import pathlib # For handling file paths as Path objects
from datetime import datetime
import logging

# REMOVE THIS LINE: from config_loader import CONFIG
# ADD THIS IMPORT:
from state_manager import StateManager # Your new state manager

# Setup module-specific logger
override_logger = logging.getLogger('OverrideManager')

# Define valid override modes for consistency
VALID_OVERRIDE_MODES = {"auto", "manual_on", "manual_off"}


def get_override_mode(state_manager: StateManager):
    """
    Determines the active override mode based on the following hierarchy:
    1. Manual override file (highest priority).
    2. Scheduled override (if no manual override is active).
    3. Default mode from StateManager (lowest priority).

    Args:
        state_manager (StateManager): The application's state manager instance.

    Returns:
        str: The determined override mode ("auto", "manual_on", "manual_off").
    """
    # --- 1. Manual override file priority ---
    # Get the path from StateManager and convert to a Path object for convenience
    manual_override_file_str = state_manager.get_value('override_file')
    if manual_override_file_str: # Ensure the path is configured
        manual_override_path = pathlib.Path(manual_override_file_str)
        if manual_override_path.exists():
            try:
                mode = manual_override_path.read_text().strip().lower()
                if mode in VALID_OVERRIDE_MODES:
                    override_logger.info(f"Manual override active from '{manual_override_path}': '{mode}'.")
                    return mode
                else:
                    override_logger.warning(
                        f"Invalid mode '{mode}' found in manual override file '{manual_override_path}'. "
                        f"Expected one of {list(VALID_OVERRIDE_MODES)}. Ignoring."
                    )
            except Exception as e:
                override_logger.error(f"Error reading or parsing manual override file '{manual_override_path}': {e}. Ignoring manual override.")
        else:
            override_logger.debug(f"Manual override file '{manual_override_path}' does not exist.")
    else:
        override_logger.debug("Manual override file path not configured in StateManager.")

    # --- 2. Schedule fallback ---
    schedule_file_str = state_manager.get_value('schedule_file')
    if schedule_file_str: # Ensure schedule file path is configured
        schedule_path = pathlib.Path(schedule_file_str)
        if schedule_path.exists():
            try:
                with open(schedule_path, "r") as f:
                    schedule = json.load(f)

                if not isinstance(schedule, dict) or "rules" not in schedule:
                    override_logger.warning(f"Invalid schedule file format in '{schedule_path}'. Missing 'rules' key or not a dictionary. Ignoring schedule.")
                    return state_manager.get_value('default_mode', 'auto') # Fallback if schedule is malformed

                now = datetime.now()
                current_hour = now.hour
                current_weekday = now.weekday()  # 0 = Monday

                for rule in schedule.get("rules", []):
                    # Basic validation for rule structure
                    if not all(k in rule for k in ["weekday", "hour", "mode"]):
                        override_logger.warning(f"Malformed rule in schedule: {rule}. Skipping.")
                        continue # Skip malformed rules

                    # Check for valid rule values
                    if not (isinstance(rule["weekday"], int) and 0 <= rule["weekday"] <= 6):
                        override_logger.warning(f"Invalid weekday '{rule['weekday']}' in schedule rule. Skipping.")
                        continue
                    if not (isinstance(rule["hour"], int) and 0 <= rule["hour"] <= 23):
                        override_logger.warning(f"Invalid hour '{rule['hour']}' in schedule rule. Skipping.")
                        continue
                    if rule["mode"] not in VALID_OVERRIDE_MODES:
                        override_logger.warning(f"Invalid mode '{rule['mode']}' in schedule rule. Skipping.")
                        continue

                    if rule["weekday"] == current_weekday and rule["hour"] == current_hour:
                        override_logger.info(f"Schedule override active: Rule matched for weekday {current_weekday}, hour {current_hour}. Mode: '{rule['mode']}'.")
                        return rule["mode"]

                override_logger.debug("No active schedule rule found for current time.")

            except json.JSONDecodeError as e:
                override_logger.error(f"Error decoding schedule file '{schedule_path}': {e}. File might be corrupted. Ignoring schedule.")
            except IOError as e:
                override_logger.error(f"I/O error reading schedule file '{schedule_path}': {e}. Ignoring schedule.")
            except Exception as e:
                override_logger.critical(f"Unexpected error processing schedule file '{schedule_path}': {e}", exc_info=True)
        else:
            override_logger.debug(f"Schedule file '{schedule_path}' does not exist.")
    else:
        override_logger.debug("Schedule file path not configured in StateManager.")

    # --- 3. Final fallback ---
    # Get default mode from StateManager
    default_mode = state_manager.get_value('default_mode', 'auto')
    override_logger.info(f"Falling back to default mode: '{default_mode}'.")
    return default_mode


# Example Usage for Testing (remove or comment out for production)
if __name__ == '__main__':
    class MockStateManager:
        def __init__(self):
            # These paths should point to dummy files for testing
            self._config = {
                'override_file': './test_manual_override.txt',
                'schedule_file': './test_schedule.json',
                'default_mode': 'auto',
                'current_mode': 'auto' # Added for completeness, though not used here
            }
            logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            override_logger.setLevel(logging.DEBUG)

            # Ensure test files are clean
            if os.path.exists(self._config['override_file']):
                os.remove(self._config['override_file'])
            if os.path.exists(self._config['schedule_file']):
                os.remove(self._config['schedule_file'])

        def get_value(self, key, default=None):
            return self._config.get(key, default)

        def set_value(self, key, value, bypass_validation=False):
            self._config[key] = value
            override_logger.debug(f"MockStateManager: Set {key} to {value}")

    print("--- Testing override_manager.py independently ---")
    mock_sm = MockStateManager()

    # --- Test 1: No override or schedule files ---
    print("\n--- Test 1: No override or schedule files ---")
    mode = get_override_mode(mock_sm)
    print(f"Determined mode: {mode}")
    assert mode == 'auto' # Should be default_mode

    # --- Test 2: Manual override file (takes priority) ---
    print("\n--- Test 2: Manual override file (takes priority) ---")
    with open(mock_sm.get_value('override_file'), 'w') as f:
        f.write("manual_on")
    mode = get_override_mode(mock_sm)
    print(f"Determined mode: {mode}")
    assert mode == 'manual_on'
    os.remove(mock_sm.get_value('override_file')) # Clean up

    # --- Test 3: Invalid manual override file content ---
    print("\n--- Test 3: Invalid manual override file content ---")
    with open(mock_sm.get_value('override_file'), 'w') as f:
        f.write("invalid_mode")
    mode = get_override_mode(mock_sm)
    print(f"Determined mode: {mode}")
    assert mode == 'auto' # Should fall back to default
    os.remove(mock_sm.get_value('override_file')) # Clean up

    # --- Test 4: Schedule active (manual file absent) ---
    print("\n--- Test 4: Schedule active (manual file absent) ---")
    # Create a schedule that's active right now
    now_test = datetime.now()
    test_schedule_data = {
        "rules": [
            {"weekday": now_test.weekday(), "hour": now_test.hour, "mode": "manual_off"}
        ]
    }
    with open(mock_sm.get_value('schedule_file'), 'w') as f:
        json.dump(test_schedule_data, f)
    
    mode = get_override_mode(mock_sm)
    print(f"Determined mode: {mode}")
    assert mode == 'manual_off'
    os.remove(mock_sm.get_value('schedule_file')) # Clean up

    # --- Test 5: Schedule inactive ---
    print("\n--- Test 5: Schedule inactive ---")
    # Create a schedule that's NOT active right now
    test_schedule_data_inactive = {
        "rules": [
            {"weekday": (now_test.weekday() + 1) % 7, "hour": now_test.hour, "mode": "manual_on"}
        ]
    }
    with open(mock_sm.get_value('schedule_file'), 'w') as f:
        json.dump(test_schedule_data_inactive, f)
    
    mode = get_override_mode(mock_sm)
    print(f"Determined mode: {mode}")
    assert mode == 'auto' # Should fall back to default
    os.remove(mock_sm.get_value('schedule_file')) # Clean up

    # --- Test 6: Corrupted schedule file ---
    print("\n--- Test 6: Corrupted schedule file ---")
    with open(mock_sm.get_value('schedule_file'), 'w') as f:
        f.write("{invalid json")
    mode = get_override_mode(mock_sm)
    print(f"Determined mode: {mode}")
    assert mode == 'auto' # Should fall back to default
    os.remove(mock_sm.get_value('schedule_file')) # Clean up

    print("\nOverride Manager tests complete.")
