# /sz/src/sensor_reader.py

"""
Module: sensor_reader.py
Purpose: Collect temperature, humidity, and motion data from GPIO sensors.
Consumes: StateManager for sensor pin configurations, calibration, and logging.
Provides: A SensorManager class with a read_sensors() method.
Behavior:
- Initializes DHT22 and PIR sensors based on pins from StateManager.
- Validates readings for plausibility.
- Maintains rolling history to detect frozen sensor states.
- Marks data as VALID, STALE, FROZEN, or ERROR.
- Updates StateManager with last known good sensor values and presence detection.
"""

import board
import adafruit_dht
import digitalio
import time
from collections import deque
import logging
from datetime import datetime # For handling timestamps if needed in future

# ADD THIS IMPORT:
from state_manager import StateManager

# Setup module-specific logger
sensor_logger = logging.getLogger('SensorManager')

# --- Helper to map BCM GPIO to CircuitPython board pins ---
# This dictionary maps the BCM GPIO numbers (used in your StateManager's config)
# to their corresponding `board` object attributes for CircuitPython libraries.
# If your config used 'board.D17' directly, this mapping wouldn't be needed,
# but it's safer to use BCM numbers in config and map here for portability.
# IMPORTANT: Verify these mappings for your specific Raspberry Pi model!
# Common RPi BCM to board mappings (Raspberry Pi 3/4)
BCM_TO_BOARD_PIN = {
    4: board.D4,
    5: board.D5,
    6: board.D6,
    7: board.D7,
    8: board.D8,
    9: board.D9,
    10: board.D10,
    11: board.D11,
    12: board.D12,
    13: board.D13,
    14: board.D14,
    15: board.D15,
    16: board.D16,
    17: board.D17, # This is the BCM 17 pin, corresponding to board.D17
    18: board.D18,
    19: board.D19,
    20: board.D20,
    21: board.D21,
    22: board.D22, # This is the BCM 22 pin, corresponding to board.D22
    23: board.D23,
    24: board.D24,
    25: board.D25,
    26: board.D26,
    27: board.D27,
}


class SensorManager:
    def __init__(self, state_manager: StateManager):
        """
        Initializes the SensorManager, setting up hardware and history buffers.

        Args:
            state_manager (StateManager): The application's state manager instance.
        """
        self.state_manager = state_manager
        self._dht = None
        self._pir = None
        self._dht_initialized = False
        self._pir_initialized = False

        # Retrieve pins from StateManager
        self._dht_bcm_pin = self.state_manager.get_value('dht_pin')
        self._pir_bcm_pin = self.state_manager.get_value('pir_pin')

        # Convert BCM pin numbers to board.DX objects
        dht_board_pin = BCM_TO_BOARD_PIN.get(self._dht_bcm_pin)
        pir_board_pin = BCM_TO_BOARD_PIN.get(self._pir_bcm_pin)

        if not dht_board_pin:
            sensor_logger.error(f"DHT pin (BCM {self._dht_bcm_pin}) not found in board mappings or not configured. DHT will not be initialized.")
        else:
            try:
                self._dht = adafruit_dht.DHT22(dht_board_pin)
                self._dht_initialized = True
                sensor_logger.info(f"DHT22 initialized on board pin {dht_board_pin} (BCM {self._dht_bcm_pin}).")
            except Exception as e:
                sensor_logger.error(f"Failed to initialize DHT22 on board pin {dht_board_pin} (BCM {self._dht_bcm_pin}): {e}")

        if not pir_board_pin:
            sensor_logger.error(f"PIR pin (BCM {self._pir_bcm_pin}) not found in board mappings or not configured. PIR will not be initialized.")
        else:
            try:
                self._pir = digitalio.DigitalInOut(pir_board_pin)
                self._pir.direction = digitalio.Direction.INPUT
                self._pir_initialized = True
                sensor_logger.info(f"PIR initialized on board pin {pir_board_pin} (BCM {self._pir_bcm_pin}).")
            except Exception as e:
                sensor_logger.error(f"Failed to initialize PIR on board pin {pir_board_pin} (BCM {self._pir_bcm_pin}): {e}")

        # Retrieve buffer size parameters from StateManager
        freeze_sensor_window = self.state_manager.get_value('freeze_sensor_window', 60) # Default 60s
        sensor_interval_sec = self.state_manager.get_value('sensor_poll_interval_sec', 30) # Default 30s

        # Calculate buffer size, ensuring we don't divide by zero
        _buffer_size = 0
        if sensor_interval_sec > 0:
            _buffer_size = max(1, freeze_sensor_window // sensor_interval_sec) # Ensure at least 1

        self._temp_history = deque(maxlen=_buffer_size)
        self._humid_history = deque(maxlen=_buffer_size)
        sensor_logger.info(f"Sensor history buffer size set to {_buffer_size} for freeze detection.")


    def _is_frozen(self, history, current_value):
        """Check if sensor value is frozen (same for entire window)."""
        if len(history) < history.maxlen:
            # Not enough data in history to determine if frozen
            return False
        # Check if all values in history are very close to the current value
        return all(abs(v - current_value) < 0.1 for v in history)

    def _build_result(self, status, temp, humid, motion, error=None):
        """Builds the standardized sensor data dictionary."""
        return {
            "status": status,
            "temperature": temp,
            "humidity": humid,
            "motion": bool(motion) if motion is not None else False,
            "timestamp": time.time(),
            "error": error if error else ""
        }

    def read_sensors(self):
        """
        Reads all sensors and returns structured result with status.
        Updates StateManager with latest sensor data and presence status.
        """
        current_temp = None
        current_humid = None
        current_motion = False
        read_error = None
        status = "ERROR" # Default status

        # --- Read DHT22 ---
        if self._dht_initialized:
            try:
                # Read humidity and temperature. Adafruit_DHT.read_retry is not used here
                # because the sensor is initialized directly. .measure() can raise errors.
                current_humid = self._dht.humidity
                current_temp = self._dht.temperature

                if current_humid is not None and current_temp is not None:
                    # Apply calibration offset from StateManager
                    dht_temp_offset = self.state_manager.get_value('dht_temp_offset', 0.0)
                    current_temp += dht_temp_offset

                    # Plausibility check
                    if not (-40 <= current_temp <= 80 and 0 <= current_humid <= 100):
                        sensor_logger.warning(f"DHT22: Out of plausible range T={current_temp}C, H={current_humid}%. Marking STALE.")
                        status = "STALE"
                    else:
                        # Check for freeze
                        frozen = self._is_frozen(self._temp_history, current_temp) and \
                                 self._is_frozen(self._humid_history, current_humid)

                        # Update history
                        self._temp_history.append(current_temp)
                        self._humid_history.append(current_humid)

                        if frozen:
                            sensor_logger.warning(f"DHT22: Temp/Humid frozen at T={current_temp}C, H={current_humid}%. Marking FROZEN.")
                            status = "FROZEN"
                        else:
                            sensor_logger.debug(f"DHT22: Temp={current_temp}C, Humidity={current_humid}%.")
                            status = "VALID"

                    # Update last known good values in StateManager, regardless of status
                    # (unless it's a hard sensor read error, in which case it stays at last_known_temp/humid)
                    self.state_manager.set_value('last_known_temp', round(current_temp, 2))
                    self.state_manager.set_value('last_known_humidity', round(current_humid, 2))
                else:
                    sensor_logger.warning("DHT22: Got None for temp or humidity. Check sensor.")
                    status = "ERROR" # Sensor gave partial None data
                    read_error = "Partial DHT read (None value)"

            except RuntimeError as error:
                # Specific Adafruit_DHT error, often 'Failed to read sensor'
                sensor_logger.error(f"DHT22 RuntimeError: {error}. Using last known values.")
                read_error = str(error)
                status = "ERROR"
            except Exception as e:
                sensor_logger.error(f"DHT22: Unexpected error during read: {e}. Using last known values.")
                read_error = str(e)
                status = "ERROR"
        else:
            sensor_logger.debug("DHT22 not initialized. Skipping temperature/humidity read.")
            status = "ERROR"
            read_error = "DHT22 not initialized."

        # If sensor read failed, use last known good values from state manager for the report
        if status == "ERROR" and (current_temp is None or current_humid is None):
            current_temp = self.state_manager.get_value('last_known_temp')
            current_humid = self.state_manager.get_value('last_known_humidity')

        # --- Read PIR Motion Sensor ---
        if self._pir_initialized:
            try:
                current_motion = self._pir.value
                self.state_manager.set_value('presence_detected', current_motion)
                sensor_logger.debug(f"PIR: Motion detected={current_motion}.")
            except Exception as e:
                sensor_logger.error(f"PIR: Error reading PIR sensor: {e}. Assuming no motion.")
                current_motion = False
                self.state_manager.set_value('presence_detected', False) # Reset presence if sensor is faulty
                # If PIR read fails, it doesn't affect DHT status, so keep original status.
        else:
            sensor_logger.debug("PIR not initialized. Skipping motion read.")


        return self._build_result(status, current_temp, current_humid, current_motion, read_error)

    def cleanup(self):
        """Clean up GPIO resources."""
        if self._dht:
            try:
                self._dht.exit()
                sensor_logger.info("DHT22 sensor cleaned up.")
            except Exception as e:
                sensor_logger.warning(f"Error during DHT22 cleanup: {e}")
        if self._pir:
            try:
                self._pir.deinit()
                sensor_logger.info("PIR sensor cleaned up.")
            except Exception as e:
                sensor_logger.warning(f"Error during PIR cleanup: {e}")

# Example Usage (for testing this module independently - remove for main integration)
if __name__ == '__main__':
    # This block simulates the StateManager for standalone testing of sensor_reader
    # and demonstrates how SensorManager is used.
    # You would NOT keep this in production main.py.
    class MockStateManager:
        def __init__(self):
            self._config = {
                # Ensure these match BCM GPIO numbers you've configured in StateManager.DEFAULT_CONFIG
                'dht_pin': 17, # Corresponds to board.D17
                'pir_pin': 22, # Corresponds to board.D22
                'dht_temp_offset': 0.5,
                'freeze_sensor_window': 60,
                'sensor_poll_interval_sec': 5,
                'last_known_temp': None,
                'last_known_humidity': None,
                'presence_detected': False,
            }
            logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            sensor_logger.setLevel(logging.DEBUG) # Enable debug for test

        def get_value(self, key, default=None):
            return self._config.get(key, default)

        def set_value(self, key, value, bypass_validation=False):
            # In a mock, we just store it
            self._config[key] = value
            sensor_logger.debug(f"MockStateManager: Set {key} to {value}")

    print("--- Testing SensorManager independently ---")
    mock_sm = MockStateManager()

    # Instantiate SensorManager using the mock state manager
    sensor_mgr = SensorManager(mock_sm)

    # Perform a few reads
    for i in range(5):
        print(f"\n--- Read {i+1} ---")
        sensor_data = sensor_mgr.read_sensors()
        print(f"Sensor Data: {sensor_data}")
        print(f"Last known temp (from mock SM): {mock_sm.get_value('last_known_temp')}")
        print(f"Presence detected (from mock SM): {mock_sm.get_value('presence_detected')}")
        time.sleep(1) # Short sleep to simulate loop interval

    # Simulate a "frozen" sensor by manually adding repetitive values to history
    print("\n--- Simulating frozen sensor ---")
    sensor_mgr._temp_history.clear()
    sensor_mgr._humid_history.clear()
    # Fill history with same value
    for _ in range(sensor_mgr._temp_history.maxlen):
        sensor_mgr._temp_history.append(25.0)
        sensor_mgr._humid_history.append(50.0)
    
    # Read again, should now be frozen
    sensor_data_frozen = sensor_mgr.read_sensors()
    print(f"Sensor Data (after simulated freeze): {sensor_data_frozen}")
    assert sensor_data_frozen['status'] == 'FROZEN'

    # Cleanup (important when using physical GPIO)
    sensor_mgr.cleanup()
    print("\nSensorManager test complete.")
