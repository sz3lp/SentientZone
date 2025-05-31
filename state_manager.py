```python
import json
import os
import threading
import time
from datetime import datetime
import uuid
import logging

# --- Setup Logging for State Manager ---
# This logger is specifically for the State Manager module.
# In a full "iron-clad" system, you'd typically have a centralized logging setup
# (e.g., configured in your main application entry point)
# where this logger contributes to a main application logger.
# For now, it logs to console/basic stream.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
state_manager_logger = logging.getLogger('StateManager')


class StateManager:
    """
    Manages all configuration and runtime state for the HVAC controller.
    Ensures thread-safe access, robust persistence, and data validation.
    This class is designed to be the single source of truth for the application's state.
    """

    CONFIG_FILE = 'config.json'
    # The time delay (in seconds) before a pending save operation actually writes to disk.
    # This is crucial for SD card endurance on Raspberry Pis, preventing excessive writes.
    # If a new change comes in before this debounce time, the timer resets.
    # We chose 30 seconds as a balance between persistence and write wear.
    # A shorter time means faster persistence of changes but more writes.
    SAVE_DEBOUNCE_TIME_SEC = 30

    # This dictionary defines the default, pristine state of the controller.
    # It's used when no config file exists or when a corrupted one is found.
    # New features should add their default values here for forward compatibility.
    DEFAULT_CONFIG = {
        # A unique identifier for this specific Raspberry Pi/HVAC zone.
        # Essential for multi-zone deployments and data aggregation later.
        # If not found or explicitly None, a new UUID will be generated on first load.
        'controller_id': None,
        'comfort_min_c': 20.0,  # Minimum desired temperature in Celsius
        'comfort_max_c': 24.0,  # Maximum desired temperature in Celsius
        'current_mode': 'auto',  # The active operational mode: 'auto', 'manual', or 'schedule'
        'manual_state': 'off',  # 'on' or 'off' when in 'manual' mode
        'schedules': [],  # A list of dictionaries, each representing a schedule entry.
                          # Example: {'name': 'Morning', 'start_time': '07:00', 'end_time': '09:00', 'temp_target': 22.0}
                          # **Larger Implementation Note:** Detailed validation of schedule format (e.g., valid time strings,
                          # non-overlapping times) is crucial but primarily handled by the UI or the Schedule Manager,
                          # not directly by the basic validation here. The StateManager just stores what it's given.
        'relay_pin': 17,  # BCM GPIO pin number connected to the HVAC relay module.
                          # **Uncertainty/Assumptions:** This assumes you're using BCM numbering.
                          # Also, the exact pin depends on your wiring. Make sure this matches!
        'dht_pin': 4,  # BCM GPIO pin number for the DHT22 data line.
                        # **Uncertainty/Assumptions:** Assumes you're using BCM numbering.
                        # Check your DHT22 wiring.
        'pir_pin': 27,  # BCM GPIO pin number for the PIR motion sensor output.
                        # **Uncertainty/Assumptions:** Assumes you're using BCM numbering.
                        # Check your PIR wiring.
        'button_gpio_pin': 26, # BCM pin for override button
        'sensor_poll_interval_sec': 30,  # How often (in seconds) the system reads sensor data.
                                         # Too frequent could waste CPU, too infrequent might miss rapid changes.
        'minimum_run_time_sec': 180,  # Minimum time (in seconds) the HVAC must run once turned on.
                                      # This is critical to protect compressors and prevent "short cycling."
                                      # 3 minutes (180s) is a common protective minimum.
        'minimum_off_time_sec': 180,  # Minimum time (in seconds) the HVAC must remain off after being turned off.
                                      # Also crucial for compressor protection.
        'dht_temp_offset': 0.0,  # A calibration offset (in Celsius) to adjust DHT22 readings.
                                  # Useful if your sensor is consistently slightly off.
        'override_schedule': False,  # A future-ready flag; potentially allows a master control to temporarily
                                      # bypass specific zone schedules without changing them.
        'last_known_temp': None,  # Stores the last valid temperature reading.
                                  # Used for graceful degradation if the DHT22 sensor temporarily fails.
                                  # The Sensor Manager module would be responsible for updating this.
        'last_known_humidity': None, # Stores the last valid humidity reading.
                                     # Used for graceful degradation if the DHT22 sensor temporarily fails.
        'hvac_status': 'unknown' # Current operational state of the HVAC system ('on', 'off', 'unknown').
                                 # This reflects the state the Actuator Control is trying to maintain.
    }

    def __init__(self):
        self._config = {}  # The internal dictionary holding the live application state.
        self._lock = threading.Lock()  # A threading lock to ensure only one thread can access/modify
                                       # _config at any given time. This prevents race conditions.
        self._last_save_time = 0       # Monotonic timestamp of the last successful disk save.
        self._pending_save = False     # Flag to indicate if a save has been requested and is awaiting debounce.

        # On initialization, immediately try to load the configuration from disk.
        self._load_config()

    def _load_config(self):
        """
        Loads configuration from the specified CONFIG_FILE.
        Handles scenarios where the file doesn't exist, is corrupted, or needs merging with new defaults.
        This method operates while holding the internal lock.
        """
        with self._lock: # Acquire the lock to ensure no other thread tries to access config during load.
            if not os.path.exists(self.CONFIG_FILE):
                # If no config file is found, start with the default configuration.
                self._config = self.DEFAULT_CONFIG.copy()
                if self._config['controller_id'] is None:
                    self._config['controller_id'] = str(uuid.uuid4()) # Generate a unique ID for this controller.
                state_manager_logger.info(f"Config file '{self.CONFIG_FILE}' not found. Created default config.")
                self._save_config_immediate() # Immediately save the new default config to disk.
                return

            try:
                # Attempt to load the JSON configuration file.
                with open(self.CONFIG_FILE, 'r') as f:
                    loaded_config = json.load(f)

                # Merge the loaded configuration with the default configuration.
                # This ensures that if new default keys are added in software updates,
                # they will be present in the loaded configuration. Existing user settings are preserved.
                self._config = self._merge_configs(self.DEFAULT_CONFIG.copy(), loaded_config)

                # Ensure controller_id exists. If it was missing in the loaded file (e.g., old version), generate it.
                if self._config.get('controller_id') is None:
                    self._config['controller_id'] = str(uuid.uuid4())
                    state_manager_logger.info("Generated new controller_id as it was missing in loaded config.")

                state_manager_logger.info(f"Config loaded successfully from '{self.CONFIG_FILE}'.")
                # Immediately save the merged config. This ensures the disk file always reflects
                # the latest schema (with new defaults added) after a load.
                self._save_config_immediate()
            except (json.JSONDecodeError, IOError) as e:
                # This block handles file corruption (JSONDecodeError) or basic file I/O errors.
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                corrupt_file = f"{self.CONFIG_FILE}.corrupt.{timestamp}"
                try:
                    # Attempt to rename the corrupted file for debugging purposes.
                    os.rename(self.CONFIG_FILE, corrupt_file)
                    state_manager_logger.warning(
                        f"Config file '{self.CONFIG_FILE}' corrupted or unreadable: {e}. "
                        f"Renamed to '{corrupt_file}' and loaded default config."
                    )
                except OSError as rename_e:
                    # If renaming fails (e.g., permission issues), log an error but still proceed with defaults.
                    state_manager_logger.error(
                        f"Could not rename corrupted config file '{self.CONFIG_FILE}': {rename_e}. "
                        "Loading default config anyway."
                    )
                # Fallback: Load the default configuration as a clean slate.
                self._config = self.DEFAULT_CONFIG.copy()
                if self._config['controller_id'] is None: # Double-check in case default also missing
                    self._config['controller_id'] = str(uuid.uuid4())
                # Immediately save the default config to ensure a valid file exists on disk.
                self._save_config_immediate()

    def _merge_configs(self, default, loaded):
        """
        Recursively merges a loaded configuration dictionary into a default configuration.
        Existing keys in 'loaded' override values in 'default'.
        New keys in 'default' that are not in 'loaded' are retained.
        This handles forward compatibility for new features.
        """
        for key, default_value in default.items():
            if key in loaded:
                if isinstance(default_value, dict) and isinstance(loaded[key], dict):
                    # If both values are dictionaries, recurse to merge nested configurations.
                    default[key] = self._merge_configs(default_value, loaded[key])
                else:
                    # For non-dictionary values, the loaded value takes precedence.
                    default[key] = loaded[key]
        return default

    def _save_config_immediate(self):
        """
        Saves the current configuration to disk immediately using an atomic write operation.
        This method is designed to be called internally (e.g., by _load_config or save_config_debounced)
        and *assumes the internal lock (`_lock`) is already acquired by the caller*.
        This prevents race conditions during the actual file write.
        """
        temp_file = self.CONFIG_FILE + '.tmp'
        try:
            # 1. Write to a temporary file first.
            with open(temp_file, 'w') as f:
                json.dump(self._config, f, indent=4)
            # 2. Atomically replace the old config file with the new temporary file.
            # os.replace() is atomic on POSIX systems (Linux/Raspberry Pi) and robust against power failures.
            # This ensures that either the old valid config or the new valid config is always present,
            # preventing corrupted files if the save operation is interrupted.
            os.replace(temp_file, self.CONFIG_FILE)
            self._last_save_time = time.monotonic() # Update the timestamp of the last save.
            self._pending_save = False # Clear the pending save flag as the save is complete.
            state_manager_logger.debug(f"Config saved immediately to '{self.CONFIG_FILE}'.")
        except IOError as e:
            # Log an error if the file write or replace operation fails.
            state_manager_logger.error(f"Failed to save config file '{self.CONFIG_FILE}': {e}")
        finally:
            # Always attempt to clean up the temporary file, even if the save failed.
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except OSError as e:
                    state_manager_logger.warning(f"Failed to clean up temp config file '{temp_file}': {e}")


    def save_config_debounced(self, force=False):
        """
        Requests a save of the configuration to disk. This method incorporates a debounce timer
        to limit the frequency of disk writes, which is important for extending the life
        of the Raspberry Pi's SD card.

        Args:
            force (bool): If True, bypasses the debounce timer and forces an immediate save.
                          Use this for critical situations like graceful shutdown or
                          when an immediate write is absolutely necessary.
        """
        with self._lock: # Acquire the lock to safely check and modify save state.
            if force:
                self._save_config_immediate()
                state_manager_logger.info("Config forced saved.")
                return

            self._pending_save = True # Mark that a save is needed.
            current_time = time.monotonic() # Get current monotonic time (unaffected by system clock changes).
            if (current_time - self._last_save_time) >= self.SAVE_DEBOUNCE_TIME_SEC:
                # If enough time has passed since the last save, perform an immediate save.
                self._save_config_immediate()
                state_manager_logger.debug("Config saved due to debounce timer.")
            else:
                # If not enough time has passed, the save is "debounced" and will happen later
                # when the timer expires (assuming a continuous check by the main loop,
                # or triggered by a subsequent set_value call after the timer expires).
                # **Larger Implementation Note:** For true robustness, a dedicated background thread
                # that periodically checks `_pending_save` and `_last_save_time` to trigger saves
                # might be considered, ensuring saves happen even if no new `set_value` calls occur.
                # For this design, we rely on `set_value` calls eventually triggering the save.
                state_manager_logger.debug("Config save debounced.")

    def get_config(self):
        """
        Returns a deep copy of the entire current configuration.
        This ensures that external modules get a snapshot of the config
        and cannot directly modify the internal state, preserving thread safety.
        """
        with self._lock: # Acquire the lock to safely read the configuration.
            # Using json.loads(json.dumps()) is a common and simple way to create a deep copy
            # of a JSON-serializable dictionary.
            return json.loads(json.dumps(self._config))

    def get_value(self, key, default=None):
        """
        Safely retrieves a single value from the configuration by its key.
        Returns the default value if the key is not found.
        """
        with self._lock: # Acquire the lock to safely read the configuration.
            return self._config.get(key, default)

    def set_value(self, key, value, bypass_validation=False):
        """
        Safely sets a single value in the configuration.
        Includes crucial input validation before accepting the value.

        Args:
            key (str): The configuration key to set.
            value: The new value for the key.
            bypass_validation (bool): Set to True ONLY for internal use (e.g., during _load_config)
                                      where values are known to be valid or are being transformed.
                                      NEVER use this for user-provided inputs.

        Returns:
            bool: True if the value was successfully set (and validated), False otherwise.
        """
        if not bypass_validation and not self._validate_value(key, value):
            state_manager_logger.warning(f"Validation failed for key '{key}' with value '{value}'. Not setting.")
            return False

        with self._lock: # Acquire the lock to safely modify the configuration.
            if key in self._config and self._config[key] == value:
                # Optimization: If the value hasn't actually changed, no need to update or save.
                return True

            self._config[key] = value
            self.save_config_debounced() # Request a debounced save after the change.
            state_manager_logger.debug(f"Key '{key}' set to '{value}'.")
            return True

    def update_values(self, updates: dict):
        """
        Updates multiple values in the configuration atomically.
        All provided values are validated before any changes are applied.
        If any value fails validation, it's skipped, but other valid updates proceed.

        Args:
            updates (dict): A dictionary of key-value pairs to update.

        Returns:
            bool: True if any values were successfully updated, False otherwise.
        """
        validated_updates = {}
        for key, value in updates.items():
            if not self._validate_value(key, value):
                state_manager_logger.warning(f"Validation failed for key '{key}' with value '{value}'. Skipping update for this key.")
            else:
                validated_updates[key] = value

        if not validated_updates:
            state_manager_logger.info("No valid updates to apply.")
            return False

        with self._lock: # Acquire the lock for the entire batch update.
            changed = False
            for key, value in validated_updates.items():
                if self._config.get(key) != value:
                    self._config[key] = value
                    changed = True
                    state_manager_logger.debug(f"Key '{key}' updated to '{value}'.")
            if changed:
                self.save_config_debounced() # Request a debounced save if any changes were made.
                return True
            return False

    def _validate_value(self, key, value):
        """
        Performs type and range validation for specific configuration keys.
        This is a critical part of the "iron-clad" design, preventing invalid data from
        corrupting the system's state.

        Returns:
            bool: True if the value is valid for the given key, False otherwise.
        """
        if key == 'comfort_min_c' or key == 'comfort_max_c':
            if not isinstance(value, (float, int)):
                state_manager_logger.error(f"Validation Error: '{key}' must be a number, got '{type(value)}'.")
                return False
            # These ranges are assumptions about typical commercial HVAC temperature requirements.
            # **Uncertainty/Assumptions:** You might need to adjust these ranges based on specific
            # industry standards, building codes, or client requirements.
            if not (0.0 <= value <= 45.0): # Allowing a broader range for control (0-45C)
                state_manager_logger.warning(f"Validation Warning: Temperature '{key}' ({value}C) is outside typical comfort range [0.0, 45.0] but within control limits.")
            return True
        elif key in ['current_mode']:
            if value not in ['auto', 'manual', 'schedule']:
                state_manager_logger.error(f"Validation Error: '{key}' must be 'auto', 'manual', or 'schedule', got '{value}'.")
                return False
            return True
        elif key in ['manual_state', 'hvac_status']:
            if value not in ['on', 'off', 'unknown']:
                state_manager_logger.error(f"Validation Error: '{key}' must be 'on', 'off', or 'unknown', got '{value}'.")
                return False
            return True
        elif key in ['relay_pin', 'dht_pin', 'pir_pin']:
            if not isinstance(value, int) or not (0 <= value <= 40): # Typical BCM GPIO pin range on Raspberry Pi.
                # **Uncertainty/Assumptions:** This range covers most standard Raspberry Pi GPIO pins.
                # Ensure your specific Pi model and any HATs/expansion boards use pins within this range.
                state_manager_logger.error(f"Validation Error: GPIO pin '{key}' ({value}) invalid or out of typical BCM range [0, 40].")
                return False
            return True
        elif key == 'controller_id':
            # controller_id is typically generated internally or managed by a deployment system.
            # Basic validation: it should be a non-empty string. UUID format check could be added.
            if not isinstance(value, str) or len(value) == 0:
                state_manager_logger.error(f"Validation Error: '{key}' must be a non-empty string, got '{value}'.")
                return False
            return True
        elif key == 'button_gpio_pin':
            if not isinstance(value, int) or not (0 <= value <= 40):
                state_manager_logger.error(f"Validation Error: GPIO pin '{key}' ({value}) invalid or out of typical BCM range [0, 40].")
                return False
            return True
        elif key == 'sensor_poll_interval_sec':
            if not isinstance(value, int) or not (5 <= value <= 600): # Allow 5 seconds to 10 minutes polling.
                state_manager_logger.error(f"Validation Error: '{key}' must be an integer between 5 and 600, got '{value}'.")
                return False
            return True
        elif key in ['minimum_run_time_sec', 'minimum_off_time_sec']:
            if not isinstance(value, int) or not (0 <= value <= 3600): # Allow 0 seconds (disable) to 1 hour (3600s).
                state_manager_logger.error(f"Validation Error: '{key}' must be an integer between 0 and 3600, got '{value}'.")
                return False
            return True
        elif key == 'dht_temp_offset':
            if not isinstance(value, (float, int)) or not (-5.0 <= value <= 5.0): # Reasonable offset range for calibration.
                state_manager_logger.error(f"Validation Error: '{key}' must be a number between -5.0 and 5.0, got '{value}'.")
                return False
            return True
        elif key == 'override_schedule':
            if not isinstance(value, bool):
                state_manager_logger.error(f"Validation Error: '{key}' must be a boolean, got '{value}'.")
                return False
            return True
        elif key in ['last_known_temp', 'last_known_humidity']:
            # These values are updated internally by sensor readings; they can be None if unknown/failed.
            if value is not None and not isinstance(value, (float, int)):
                state_manager_logger.error(f"Validation Error: '{key}' must be a number or None, got '{value}'.")
                return False
            return True
        elif key == 'schedules':
            # **Larger Implementation Note:** This validation is relatively basic for a list of schedules.
            # For a truly "iron-clad" system managing complex commercial schedules, you would want:
            # 1. More detailed validation of each schedule dictionary's structure (name, start_time, end_time, temp_target).
            # 2. Validation of time formats (e.g., "HH:MM").
            # 3. Logic to check for overlapping schedules within the list.
            # 4. Range checks for `temp_target` within schedules.
            # These complex validations are typically handled by a dedicated 'Schedule Manager' module
            # or the UI itself *before* trying to pass the list to the StateManager.
            if not isinstance(value, list):
                state_manager_logger.error(f"Validation Error: '{key}' must be a list, got '{type(value)}'.")
                return False
            return True # Assuming individual schedule items are validated elsewhere if needed.
        else:
            # **Uncertainty/Assumptions:** For any key not explicitly defined in the validation rules,
            # this defaults to True. This allows for adding new keys to DEFAULT_CONFIG without
            # immediately requiring validation logic here. However, for maximum "iron-clad" security,
            # you might want to enforce explicit validation for *all* keys to prevent unexpected data types.
            state_manager_logger.warning(f"Validation Warning: No explicit validation rule for key '{key}'. Proceeding assuming valid.")
            return True

# --- Example Usage for Testing and Integration ---
# This block demonstrates how the StateManager works in isolation.
# It simulates various scenarios like first-time load, setting values,
# testing debounce, handling corruption, and forward compatibility.
# You would remove or comment out this block when integrating into your main application.
if __name__ == "__main__":
    # Ensure a clean slate for testing by deleting any existing config files.
    if os.path.exists(StateManager.CONFIG_FILE):
        os.remove(StateManager.CONFIG_FILE)
    if os.path.exists(StateManager.CONFIG_FILE + '.tmp'):
        os.remove(StateManager.CONFIG_FILE + '.tmp')
    # Clean up any previously created corrupted files from past tests.
    for f in os.listdir('.'):
        if f.startswith(StateManager.CONFIG_FILE + '.corrupt.'):
            os.remove(f)

    print("--- Test 1: Initial load (no file) ---")
    # First time loading should create a default config.json and generate a controller_id.
    sm = StateManager()
    initial_config = sm.get_config()
    print(f"Initial config loaded: {initial_config}")
    assert initial_config['current_mode'] == 'auto'
    assert isinstance(initial_config['controller_id'], str) # Check that a UUID was generated.
    assert os.path.exists(StateManager.CONFIG_FILE) # Verify config file was created.

    print("\n--- Test 2: Set values and trigger debounced save ---")
    sm.set_value('comfort_min_c', 21.0)
    sm.set_value('current_mode', 'manual')
    sm.set_value('manual_state', 'on')
    # These calls should trigger internal flags for debounced saving.
    # The file might not be immediately updated on disk due to the debounce timer.

    print("\n--- Test 3: Validate input (should fail and log warnings) ---")
    sm.set_value('comfort_min_c', 'twenty') # This should fail validation (wrong type).
    sm.set_value('relay_pin', 999) # This should fail validation (out of typical GPIO range).
    sm.set_value('current_mode', 'invalid_mode') # This should fail validation (invalid option).

    # Verify that the values that failed validation were NOT changed.
    current_config = sm.get_config()
    assert current_config['comfort_min_c'] == 21.0 # Should remain 21.0
    assert current_config['relay_pin'] == StateManager.DEFAULT_CONFIG['relay_pin'] # Should revert/stay at default
    assert current_config['current_mode'] == 'manual' # Should remain 'manual'

    # Add a schedule to the list.
    # **Important Note on Lists/Dictionaries:** When modifying mutable objects (like lists or dictionaries)
    # returned by `get_value` or `get_config`, you must re-`set_value` the entire object
    # back into the StateManager for the changes to be recognized and persisted.
    print("\n--- Test 4: Add a schedule ---")
    current_schedules = sm.get_value('schedules')
    new_schedule = {'name': 'Evening', 'start_time': '18:00', 'end_time': '22:00', 'temp_target': 23.5}
    current_schedules.append(new_schedule)
    sm.set_value('schedules', current_schedules) # Re-set the entire list to trigger save.

    # Force a save to ensure all changes from previous steps are written to disk
    # before the next test (which simulates a new startup).
    sm.save_config_debounced(force=True)
    time.sleep(1) # Give a moment for file operations to complete.

    print("\n--- Test 5: Load existing config from disk ---")
    # Create a new StateManager instance to simulate a fresh application startup.
    sm2 = StateManager()
    loaded_config = sm2.get_config()
    print(f"Loaded config: {loaded_config}")
    assert loaded_config['comfort_min_c'] == 21.0
    assert loaded_config['current_mode'] == 'manual'
    assert loaded_config['manual_state'] == 'on'
    assert len(loaded_config['schedules']) == 1
    assert loaded_config['schedules'][0]['name'] == 'Evening'

    print("\n--- Test 6: Test corrupted file recovery (manually create a bad file) ---")
    # Intentionally corrupt the config file to test error handling.
    with open(StateManager.CONFIG_FILE, 'w') as f:
        f.write("{invalid json")
    sm3 = StateManager()
    corrupted_load_config = sm3.get_config()
    print(f"Loaded config after corruption: {corrupted_load_config}")
    # Verify that the system reverted to default configuration after detecting corruption.
    assert corrupted_load_config == StateManager.DEFAULT_CONFIG
    # Verify that the corrupted file was renamed with a timestamp.
    # (Note: The exact timestamp will vary, so we check for presence and prefix).
    assert any(f.startswith(f"{StateManager.CONFIG_FILE}.corrupt.") for f in os.listdir('.'))

    print("\n--- Test 7: Forward compatibility (add a new default key, then load an old config) ---")
    # Simulate an old config file that doesn't have a 'new_feature_setting'.
    old_config_content = {
        'comfort_min_c': 19.0,
        'current_mode': 'auto',
        'controller_id': 'test-old-id'
    }
    with open(StateManager.CONFIG_FILE, 'w') as f:
        json.dump(old_config_content, f)

    # Temporarily add a new key to DEFAULT_CONFIG to simulate a software update.
    StateManager.DEFAULT_CONFIG['new_feature_setting'] = 'default_value_for_new_feature'
    sm4 = StateManager()
    forward_compatible_config = sm4.get_config()
    print(f"Forward compatible config: {forward_compatible_config}")
    # Verify that the old settings are preserved and the new default key is added.
    assert forward_compatible_config['comfort_min_c'] == 19.0
    assert forward_compatible_config['new_feature_setting'] == 'default_value_for_new_feature'
    assert forward_compatible_config['controller_id'] == 'test-old-id'
    # Clean up the temporary modification to DEFAULT_CONFIG for subsequent runs.
    del StateManager.DEFAULT_CONFIG['new_feature_setting']

    print("\nAll StateManager tests passed successfully!")
    print("Remember to integrate this `StateManager` class into your main application's logic.")
    print("You'll instantiate it once and pass its instance to other modules as needed.")

    # Final cleanup of all test files.
    if os.path.exists(StateManager.CONFIG_FILE):
        os.remove(StateManager.CONFIG_FILE)
    if os.path.exists(StateManager.CONFIG_FILE + '.tmp'):
        os.remove(StateManager.CONFIG_FILE + '.tmp')
    for f in os.listdir('.'):
        if f.startswith(StateManager.CONFIG_FILE + '.corrupt.'):
            os.remove(f)

```
