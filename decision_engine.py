# /sz/src/decision_engine.py

"""
Module: decision_engine.py
Purpose: Determine HVAC action based on sensor input, config, and override state.
Consumes:
- sensor_data from SensorManager.read_sensors()
- override_mode: one of ["auto", "manual_on", "manual_off"]
- StateManager for HVAC control parameters (comfort ranges).
Provides:
- decision: dict with 'hvac_state', 'mode', 'cause'.
This is a pure logic module: no GPIO, no I/O.
"""

import logging

# REMOVE THIS LINE: from config_loader import CONFIG
# ADD THIS IMPORT:
from state_manager import StateManager

# Setup module-specific logger
decision_logger = logging.getLogger('DecisionEngine')

# All valid output states
VALID_STATES = ["HEAT_ON", "COOL_ON", "FAN_ONLY", "OFF"]


def decide_hvac_action(sensor_data: dict, override_mode: str, state_manager: StateManager) -> dict:
    """
    Determines the desired HVAC action based on current sensor readings,
    system override mode, and configured comfort parameters.

    Args:
        sensor_data (dict): Dictionary from SensorManager containing
                            'status', 'motion', 'temperature', 'humidity'.
        override_mode (str): Current override mode (e.g., "auto", "manual_on", "manual_off").
        state_manager (StateManager): The application's state manager instance.

    Returns:
        dict: {
            'hvac_state': str,   # e.g., "HEAT_ON", "COOL_ON", "FAN_ONLY", "OFF"
            'mode': str,         # e.g., "AUTO", "MANUAL", "FAILSAFE"
            'cause': str         # e.g., "HUMAN_OVERRIDE", "SENSOR_FREEZE", "TEMP_HIGH", etc.
        }
    """
    status = sensor_data.get("status")
    motion = sensor_data.get("motion")
    temp = sensor_data.get("temperature")
    humid = sensor_data.get("humidity")

    # Log incoming data for debugging
    decision_logger.debug(f"Sensor Data: Status={status}, Motion={motion}, Temp={temp}C, Humid={humid}%")
    decision_logger.debug(f"Override Mode: {override_mode}")

    # --- Apply Manual Override Priority ---
    if override_mode == "manual_on":
        decision_logger.info("Manual ON override active. Setting HVAC state to FAN_ONLY.")
        result = _build("FAN_ONLY", "MANUAL", "HUMAN_OVERRIDE")
        # Store the decision in StateManager
        state_manager.set_value('hvac_current_state', result['hvac_state'])
        state_manager.set_value('hvac_current_mode', result['mode'])
        state_manager.set_value('hvac_current_cause', result['cause'])
        return result

    if override_mode == "manual_off":
        decision_logger.info("Manual OFF override active. Setting HVAC state to OFF.")
        result = _build("OFF", "MANUAL", "HUMAN_OVERRIDE")
        # Store the decision in StateManager
        state_manager.set_value('hvac_current_state', result['hvac_state'])
        state_manager.set_value('hvac_current_mode', result['mode'])
        state_manager.set_value('hvac_current_cause', result['cause'])
        return result

    # --- Sensor Status Check (Failsafe) ---
    if status in ["ERROR", "FROZEN"]:
        decision_logger.warning(f"Sensor status is '{status}'. Activating FAILSAFE mode.")
        result = _build("OFF", "FAILSAFE", f"SENSOR_{status.upper()}")
        # Store the decision in StateManager
        state_manager.set_value('hvac_current_state', result['hvac_state'])
        state_manager.set_value('hvac_current_mode', result['mode'])
        state_manager.set_value('hvac_current_cause', result['cause'])
        return result

    # Handle cases where valid temp/humid are missing but status is not ERROR/FROZEN
    # (e.g., if a sensor momentarily returns None without error status)
    if temp is None:
        decision_logger.warning("Temperature data is None. Cannot make temperature-based decision. Defaulting to OFF.")
        result = _build("OFF", "FAILSAFE", "MISSING_TEMP_DATA")
        state_manager.set_value('hvac_current_state', result['hvac_state'])
        state_manager.set_value('hvac_current_mode', result['mode'])
        state_manager.set_value('hvac_current_cause', result['cause'])
        return result


    # --- Retrieve Comfort Parameters from StateManager ---
    temp_min_comfort = state_manager.get_value('temp_min_comfort', 20.0) # Default 20C
    temp_max_comfort = state_manager.get_value('temp_max_comfort', 24.0) # Default 24C
    humid_min_comfort = state_manager.get_value('humid_min_comfort', 30.0) # Default 30%
    humid_max_comfort = state_manager.get_value('humid_max_comfort', 60.0) # Default 60%

    decision_logger.debug(f"Comfort Ranges: Temp {temp_min_comfort}-{temp_max_comfort}C, Humid {humid_min_comfort}-{humid_max_comfort}%")


    # --- Occupancy-based Logic ---
    if motion:
        decision_logger.debug(f"Motion detected. Current temp: {temp}C.")
        if temp < temp_min_comfort:
            decision_logger.info(f"Occupied and too cold ({temp}C < {temp_min_comfort}C). Activating HEAT_ON.")
            result = _build("HEAT_ON", "AUTO", "TEMP_LOW")
        elif temp > temp_max_comfort:
            decision_logger.info(f"Occupied and too hot ({temp}C > {temp_max_comfort}C). Activating COOL_ON.")
            result = _build("COOL_ON", "AUTO", "TEMP_HIGH")
        else:
            decision_logger.info(f"Occupied and temp {temp}C within comfort range. HVAC OFF.")
            result = _build("OFF", "AUTO", "COMFORT_RANGE")
    else:
        # --- No motion → Relax to off unless humidity critical ---
        decision_logger.debug(f"No motion detected. Current temp: {temp}C, Humid: {humid}%.")
        if humid is not None:
            if humid < humid_min_comfort:
                decision_logger.info(f"Unoccupied and humidity too low ({humid}% < {humid_min_comfort}%). Activating FAN_ONLY for circulation.")
                result = _build("FAN_ONLY", "AUTO", "DRY_IDLE")
            elif humid > humid_max_comfort:
                decision_logger.info(f"Unoccupied and humidity too high ({humid}% > {humid_max_comfort}%). Activating FAN_ONLY for circulation.")
                result = _build("FAN_ONLY", "AUTO", "HUMID_IDLE")
            else:
                decision_logger.info(f"Unoccupied and all parameters OK. HVAC OFF.")
                result = _build("OFF", "AUTO", "UNOCCUPIED")
        else:
            # If humidity is None and no motion, default to OFF
            decision_logger.warning("No motion and humidity data is None. Defaulting to OFF.")
            result = _build("OFF", "AUTO", "UNOCCUPIED_NO_HUMID")

    # --- Store the final decision in StateManager ---
    state_manager.set_value('hvac_current_state', result['hvac_state'])
    state_manager.set_value('hvac_current_mode', result['mode'])
    state_manager.set_value('hvac_current_cause', result['cause'])
    
    decision_logger.info(f"Final HVAC Decision: State='{result['hvac_state']}', Mode='{result['mode']}', Cause='{result['cause']}'.")
    return result


def _build(state: str, mode: str, cause: str) -> dict:
    """Helper to build the decision dictionary."""
    if state not in VALID_STATES:
        decision_logger.error(f"Attempted to build decision with invalid HVAC state: {state}")
        state = "OFF" # Default to a safe state
        cause = "INVALID_STATE_REQUESTED"
    return {
        "hvac_state": state,
        "mode": mode,
        "cause": cause
    }

# Example Usage for Testing (remove for main integration)
if __name__ == '__main__':
    class MockStateManager:
        def __init__(self):
            self._config = {
                'temp_min_comfort': 20.0,
                'temp_max_comfort': 24.0,
                'humid_min_comfort': 30.0,
                'humid_max_comfort': 60.0,
                'hvac_current_state': "OFF",
                'hvac_current_mode': "INIT",
                'hvac_current_cause': "BOOT",
            }
            logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            decision_logger.setLevel(logging.DEBUG)

        def get_value(self, key, default=None):
            return self._config.get(key, default)

        def set_value(self, key, value, bypass_validation=False):
            self._config[key] = value
            decision_logger.debug(f"MockStateManager: Set '{key}' to '{value}'")

    print("--- Testing decision_engine.py independently ---")
    mock_sm = MockStateManager()

    # --- Test 1: Manual ON override ---
    print("\n--- Test 1: Manual ON override ---")
    sensor_data_mock = {'status': 'VALID', 'motion': False, 'temperature': 22.0, 'humidity': 50.0}
    decision = decide_hvac_action(sensor_data_mock, "manual_on", mock_sm)
    print(f"Decision: {decision}")
    assert decision['hvac_state'] == 'FAN_ONLY'
    assert decision['mode'] == 'MANUAL'
    assert mock_sm.get_value('hvac_current_state') == 'FAN_ONLY'

    # --- Test 2: Manual OFF override ---
    print("\n--- Test 2: Manual OFF override ---")
    decision = decide_hvac_action(sensor_data_mock, "manual_off", mock_sm)
    print(f"Decision: {decision}")
    assert decision['hvac_state'] == 'OFF'
    assert decision['mode'] == 'MANUAL'
    assert mock_sm.get_value('hvac_current_state') == 'OFF'

    # --- Test 3: Sensor ERROR ---
    print("\n--- Test 3: Sensor ERROR ---")
    sensor_data_error = {'status': 'ERROR', 'motion': True, 'temperature': None, 'humidity': None}
    decision = decide_hvac_action(sensor_data_error, "auto", mock_sm)
    print(f"Decision: {decision}")
    assert decision['hvac_state'] == 'OFF'
    assert decision['mode'] == 'FAILSAFE'
    assert decision['cause'] == 'SENSOR_ERROR'

    # --- Test 4: Occupied & Too Cold ---
    print("\n--- Test 4: Occupied & Too Cold ---")
    sensor_data_cold = {'status': 'VALID', 'motion': True, 'temperature': 19.0, 'humidity': 50.0}
    decision = decide_hvac_action(sensor_data_cold, "auto", mock_sm)
    print(f"Decision: {decision}")
    assert decision['hvac_state'] == 'HEAT_ON'
    assert decision['mode'] == 'AUTO'
    assert decision['cause'] == 'TEMP_LOW'

    # --- Test 5: Occupied & Too Hot ---
    print("\n--- Test 5: Occupied & Too Hot ---")
    sensor_data_hot = {'status': 'VALID', 'motion': True, 'temperature': 25.0, 'humidity': 50.0}
    decision = decide_hvac_action(sensor_data_hot, "auto", mock_sm)
    print(f"Decision: {decision}")
    assert decision['hvac_state'] == 'COOL_ON'
    assert decision['mode'] == 'AUTO'
    assert decision['cause'] == 'TEMP_HIGH'

    # --- Test 6: Occupied & Comfort Range ---
    print("\n--- Test 6: Occupied & Comfort Range ---")
    sensor_data_comfort = {'status': 'VALID', 'motion': True, 'temperature': 22.0, 'humidity': 50.0}
    decision = decide_hvac_action(sensor_data_comfort, "auto", mock_sm)
    print(f"Decision: {decision}")
    assert decision['hvac_state'] == 'OFF'
    assert decision['mode'] == 'AUTO'
    assert decision['cause'] == 'COMFORT_RANGE'

    # --- Test 7: Unoccupied & Too Dry ---
    print("\n--- Test 7: Unoccupied & Too Dry ---")
    sensor_data_dry_idle = {'status': 'VALID', 'motion': False, 'temperature': 22.0, 'humidity': 25.0}
    decision = decide_hvac_action(sensor_data_dry_idle, "auto", mock_sm)
    print(f"Decision: {decision}")
    assert decision['hvac_state'] == 'FAN_ONLY'
    assert decision['mode'] == 'AUTO'
    assert decision['cause'] == 'DRY_IDLE'

    # --- Test 8: Unoccupied & Too Humid ---
    print("\n--- Test 8: Unoccupied & Too Humid ---")
    sensor_data_humid_idle = {'status': 'VALID', 'motion': False, 'temperature': 22.0, 'humidity': 65.0}
    decision = decide_hvac_action(sensor_data_humid_idle, "auto", mock_sm)
    print(f"Decision: {decision}")
    assert decision['hvac_state'] == 'FAN_ONLY'
    assert decision['mode'] == 'AUTO'
    assert decision['cause'] == 'HUMID_IDLE'

    # --- Test 9: Unoccupied & All OK ---
    print("\n--- Test 9: Unoccupied & All OK ---")
    sensor_data_unoccupied_ok = {'status': 'VALID', 'motion': False, 'temperature': 22.0, 'humidity': 50.0}
    decision = decide_hvac_action(sensor_data_unoccupied_ok, "auto", mock_sm)
    print(f"Decision: {decision}")
    assert decision['hvac_state'] == 'OFF'
    assert decision['mode'] == 'AUTO'
    assert decision['cause'] == 'UNOCCUPIED'

    # --- Test 10: Unoccupied, No Humidity Data ---
    print("\n--- Test 10: Unoccupied, No Humidity Data ---")
    sensor_data_unoccupied_no_humid = {'status': 'VALID', 'motion': False, 'temperature': 22.0, 'humidity': None}
    decision = decide_hvac_action(sensor_data_unoccupied_no_humid, "auto", mock_sm)
    print(f"Decision: {decision}")
    assert decision['hvac_state'] == 'OFF'
    assert decision['mode'] == 'AUTO'
    assert decision['cause'] == 'UNOCCUPIED_NO_HUMID'

    print("\nDecision Engine tests complete.")
