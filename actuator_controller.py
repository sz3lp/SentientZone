# /sz/src/actuator_control.py

"""
Module: actuator_control.py
Purpose: Interface with Raspberry Pi GPIOs to control HVAC relays and read feedback.
         Designed for 24V AC conventional thermostat wiring.
Consumes:
- StateManager for GPIO pin assignments and configuration.
Produces:
- Activates/deactivates GPIOs to control HVAC functions (Cool, Heat, Fan).
- Reads GPIOs to provide feedback on active HVAC lines (optional).
Behavior:
- Initializes GPIOs at startup.
- Provides functions to set HVAC states (ON/OFF, mode, fan).
- Provides functions to read current HVAC line states.
- Cleans up GPIOs on shutdown.
"""

import logging
import time

# Attempt to import RPi.GPIO for actual hardware control
# If not available (e.g., running on non-Pi or for testing), use a mock.
try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM) # Use Broadcom SOC channel numbers, not board numbers
    GPIO_AVAILABLE = True
    actuator_logger = logging.getLogger('ActuatorControl')
    actuator_logger.info("RPi.GPIO detected. Actuator control will interface with hardware.")
except ImportError:
    # Mock RPi.GPIO for development/testing on non-Pi environments
    actuator_logger = logging.getLogger('ActuatorControl')
    actuator_logger.warning("RPi.GPIO not detected. Actuator control running in MOCK mode. No physical GPIO control.")
    
    class MockGPIO:
        OUT = "OUT"
        IN = "IN"
        HIGH = "HIGH"
        LOW = "LOW"
        BCM = "BCM"
        PUD_UP = "PUD_UP" # Pull-up resistor for inputs

        def setmode(self, mode):
            actuator_logger.debug(f"MockGPIO: setmode({mode})")
        def setup(self, pin, mode, initial=LOW, pull_up_down=None):
            actuator_logger.debug(f"MockGPIO: setup pin {pin}, mode {mode}, initial {initial}, pull_up_down {pull_up_down}")
            if mode == self.OUT:
                setattr(self, f'_pin_state_{pin}', initial)
            elif mode == self.IN:
                setattr(self, f'_pin_state_{pin}', self.LOW) # Default input to LOW
        def output(self, pin, state):
            actuator_logger.debug(f"MockGPIO: output pin {pin}, state {state}")
            setattr(self, f'_pin_state_{pin}', state)
        def input(self, pin):
            # In mock mode, inputs return LOW by default.
            # For testing specific feedback, you could modify this mock.
            state = getattr(self, f'_pin_state_{pin}', self.LOW)
            actuator_logger.debug(f"MockGPIO: input pin {pin} -> {state}")
            return state
        def cleanup(self):
            actuator_logger.debug("MockGPIO: cleanup")
        def add_event_detect(self, pin, edge, callback=None, bouncetime=None):
            actuator_logger.debug(f"MockGPIO: add_event_detect({pin}, {edge})")
        def remove_event_detect(self, pin):
            actuator_logger.debug(f"MockGPIO: remove_event_detect({pin})")

    GPIO = MockGPIO()
    GPIO_AVAILABLE = False


# Import StateManager (assuming it's in the same /sz/src directory)
from state_manager import StateManager

# --- Global Actuator State and Pin Mapping ---
# These will be initialized from StateManager config
control_pins = {} # e.g., {'Y_PIN': 17, 'G_PIN': 27, 'W_PIN': 22}
feedback_pins = {} # e.g., {'Y_FEEDBACK_PIN': 23, 'G_FEEDBACK_PIN': 24}

# Mapping of HVAC functions to control pins (keys must match config)
HVAC_FUNCTIONS = {
    "COOL": "Y_PIN",
    "HEAT": "W_PIN",
    "FAN_ONLY": "G_PIN",
    # Add other functions if needed, e.g., "EMERGENCY_HEAT": "E_PIN", "REVERSING_VALVE": "O_B_PIN"
}

# --- Initialization and Cleanup ---

def setup_actuators(state_manager: StateManager):
    """
    Initializes GPIO pins based on configuration from StateManager.
    Sets up output pins for relays and input pins for feedback.
    """
    global control_pins, feedback_pins

    # Retrieve pin configurations from StateManager
    # These keys MUST match what you put in your config.json (and StateManager defaults)
    control_pins_config = state_manager.get_value('hvac_control_gpio_pins', {})
    feedback_pins_config = state_manager.get_value('hvac_feedback_gpio_pins', {})

    if not control_pins_config:
        actuator_logger.error("No HVAC control GPIO pins configured. Actuator control will be limited.")
        return False # Indicate setup failure

    control_pins = {func: control_pins_config.get(func) for func in HVAC_FUNCTIONS.values() if control_pins_config.get(func) is not None}
    feedback_pins = {func: feedback_pins_config.get(func) for func in control_pins.keys() if feedback_pins_config.get(func) is not None} # Only feedback for defined control pins

    if not control_pins:
        actuator_logger.error("No valid HVAC control GPIO pins found in config. Actuator control cannot be set up.")
        return False

    actuator_logger.info(f"Configuring HVAC control pins: {control_pins}")
    actuator_logger.info(f"Configuring HVAC feedback pins: {feedback_pins}")

    try:
        # Setup output pins for relays
        for func_key, pin in control_pins.items():
            if pin is not None:
                # Relays are typically 'active LOW' (GPIO LOW turns relay ON) or 'active HIGH'.
                # For safety, initialize all control pins to OFF state (e.g., HIGH for active-LOW relays).
                # Assume active HIGH relays for this example (GPIO HIGH turns relay ON, LOW is OFF).
                GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)
                actuator_logger.debug(f"GPIO {pin} ({func_key}) set as output, initial LOW (OFF).")

        # Setup input pins for feedback (with pull-up for optocoupler common configuration)
        for func_key, pin in feedback_pins.items():
            if pin is not None:
                # Assuming optocoupler setup where input is HIGH when 24V line is active
                GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP) # Use PUD_UP for typical optocoupler pull-down on input
                actuator_logger.debug(f"GPIO {pin} ({func_key}) set as input with pull-up.")
        
        actuator_logger.info("Actuator GPIOs initialized successfully.")
        return True # Indicate successful setup

    except Exception as e:
        actuator_logger.critical(f"Failed to setup actuator GPIOs: {e}", exc_info=True)
        return False # Indicate setup failure


def cleanup_actuators():
    """
    Cleans up all GPIO pins used by the actuator module.
    Crucial to call on application exit to release resources.
    """
    if GPIO_AVAILABLE:
        try:
            # Ensure all control pins are turned OFF before cleanup
            for func_key, pin in control_pins.items():
                if pin is not None:
                    GPIO.output(pin, GPIO.LOW) # Set all relays to OFF state
                    actuator_logger.debug(f"GPIO {pin} ({func_key}) set to LOW (OFF) before cleanup.")
            
            GPIO.cleanup()
            actuator_logger.info("Actuator GPIOs cleaned up successfully.")
        except Exception as e:
            actuator_logger.error(f"Error during actuator GPIO cleanup: {e}", exc_info=True)
    else:
        actuator_logger.debug("Skipping GPIO cleanup in MOCK mode.")


# --- HVAC Control Functions ---

def set_hvac_state(mode: str, fan_state: str, state_manager: StateManager):
    """
    Activates/deactivates HVAC control lines based on desired mode and fan state.
    
    Args:
        mode (str): Desired HVAC mode ("OFF", "COOL", "HEAT", "FAN_ONLY").
        fan_state (str): Desired fan state ("AUTO", "ON").
        state_manager (StateManager): The application's state manager.
    Returns:
        bool: True if state change initiated, False otherwise.
    """
    if not GPIO_AVAILABLE:
        actuator_logger.warning(f"Attempted to set HVAC state in MOCK mode: Mode={mode}, Fan={fan_state}. No physical action.")
        return False

    actuator_logger.info(f"Attempting to set HVAC to Mode: {mode}, Fan: {fan_state}")

    # All pins are turned OFF initially to ensure a clean state change
    for func_key, pin in control_pins.items():
        if pin is not None:
            GPIO.output(pin, GPIO.LOW) # Turn all relays OFF
            actuator_logger.debug(f"GPIO {pin} (initially OFF) for {func_key}.")

    # Apply the desired state
    success = False
    try:
        # Fan control (G wire)
        if fan_state == "ON" or mode == "FAN_ONLY":
            if control_pins.get(HVAC_FUNCTIONS["FAN_ONLY"]) is not None:
                GPIO.output(control_pins[HVAC_FUNCTIONS["FAN_ONLY"]], GPIO.HIGH)
                actuator_logger.info(f"Fan ON (GPIO {control_pins[HVAC_FUNCTIONS['FAN_ONLY']]}).")
                success = True
            else:
                actuator_logger.warning("Fan control pin not configured.")
        
        # Mode control (Y for Cool, W for Heat)
        if mode == "COOL":
            if control_pins.get(HVAC_FUNCTIONS["COOL"]) is not None:
                GPIO.output(control_pins[HVAC_FUNCTIONS["COOL"]], GPIO.HIGH)
                actuator_logger.info(f"Cooling ON (GPIO {control_pins[HVAC_FUNCTIONS['COOL']]}).")
                success = True
            else:
                actuator_logger.warning("Cooling control pin not configured.")
        elif mode == "HEAT":
            if control_pins.get(HVAC_FUNCTIONS["HEAT"]) is not None:
                GPIO.output(control_pins[HVAC_FUNCTIONS["HEAT"]], GPIO.HIGH)
                actuator_logger.info(f"Heating ON (GPIO {control_pins[HVAC_FUNCTIONS['HEAT']]}).")
                success = True
            else:
                actuator_logger.warning("Heating control pin not configured.")
        elif mode == "OFF":
            actuator_logger.info("HVAC set to OFF (all control pins deactivated).")
            success = True # All pins were turned off initially
        
        # If the fan_state is "AUTO" and the mode is not "FAN_ONLY", the fan will be off
        # unless activated by the COOL/HEAT call. This is standard thermostat behavior.

        state_manager.set_value('current_hvac_mode', mode)
        state_manager.set_value('current_fan_state', fan_state)
        state_manager.save_config_debounced() # Save state immediately after action
        return success

    except Exception as e:
        actuator_logger.error(f"Error setting HVAC state to {mode}: {e}", exc_info=True)
        return False

def get_hvac_feedback():
    """
    Reads the state of HVAC control lines via feedback GPIOs.
    Assumes feedback pins are configured to read HIGH when 24V line is active.

    Returns:
        dict: A dictionary indicating the active state of each monitored HVAC line.
              e.g., {'Y_FEEDBACK_PIN': True, 'G_FEEDBACK_PIN': False}
              Returns empty dict if no feedback pins are configured or in mock mode.
    """
    if not GPIO_AVAILABLE or not feedback_pins:
        actuator_logger.debug("No HVAC feedback pins configured or in MOCK mode. Cannot read feedback.")
        return {}

    feedback_status = {}
    try:
        for func_key, pin in feedback_pins.items():
            if pin is not None:
                status = GPIO.input(pin) == GPIO.HIGH
                feedback_status[func_key] = status
                actuator_logger.debug(f"Feedback {func_key} (GPIO {pin}): {'ACTIVE' if status else 'INACTIVE'}")
    except Exception as e:
        actuator_logger.error(f"Error reading HVAC feedback GPIOs: {e}", exc_info=True)
    
    return feedback_status

# --- Example Usage for Independent Testing (remove for main integration) ---
if __name__ == '__main__':
    # Setup basic logging for standalone execution
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    actuator_logger.setLevel(logging.DEBUG)

    class MockStateManager:
        def __init__(self):
            # Define mock GPIOs for a simplified setup (e.g., Cool, Fan, Heat)
            self._config = {
                'hvac_control_gpio_pins': {
                    'Y_PIN': 17,  # GPIO for Cooling
                    'G_PIN': 27,  # GPIO for Fan
                    'W_PIN': 22   # GPIO for Heating
                },
                'hvac_feedback_gpio_pins': {
                    'Y_FEEDBACK_PIN': 23, # Optional: GPIO to read Y line state
                    'G_FEEDBACK_PIN': 24  # Optional: GPIO to read G line state
                },
                'current_hvac_mode': 'OFF',
                'current_fan_state': 'AUTO'
            }
            self.saved_config = {}

        def get_value(self, key, default=None):
            return self._config.get(key, default)

        def set_value(self, key, value, bypass_validation=False):
            self._config[key] = value

        def save_config_debounced(self, force=False):
            self.saved_config.update(self._config)
            actuator_logger.info(f"MockStateManager: Config saved. Current state: {self.saved_config['current_hvac_mode']}, {self.saved_config['current_fan_state']}")
            
    print("--- Testing actuator_control.py independently ---")
    mock_sm = MockStateManager()

    if setup_actuators(mock_sm):
        print("\n--- Test 1: Set to COOL (Fan Auto) ---")
        set_hvac_state("COOL", "AUTO", mock_sm)
        # In real mode, wait a bit for system to react
        time.sleep(2) 
        print(f"Current HVAC Mode (StateManager): {mock_sm.get_value('current_hvac_mode')}")
        print(f"Current Fan State (StateManager): {mock_sm.get_value('current_fan_state')}")
        feedback = get_hvac_feedback()
        print(f"HVAC Feedback: {feedback}") # In mock mode, this will be empty or default LOW

        print("\n--- Test 2: Set to FAN_ONLY (Fan ON) ---")
        set_hvac_state("FAN_ONLY", "ON", mock_sm)
        time.sleep(2)
        print(f"Current HVAC Mode (StateManager): {mock_sm.get_value('current_hvac_mode')}")
        print(f"Current Fan State (StateManager): {mock_sm.get_value('current_fan_state')}")
        feedback = get_hvac_feedback()
        print(f"HVAC Feedback: {feedback}")

        print("\n--- Test 3: Set to HEAT (Fan Auto) ---")
        set_hvac_state("HEAT", "AUTO", mock_sm)
        time.sleep(2)
        print(f"Current HVAC Mode (StateManager): {mock_sm.get_value('current_hvac_mode')}")
        print(f"Current Fan State (StateManager): {mock_sm.get_value('current_fan_state')}")
        feedback = get_hvac_feedback()
        print(f"HVAC Feedback: {feedback}")

        print("\n--- Test 4: Set to OFF ---")
        set_hvac_state("OFF", "AUTO", mock_sm)
        time.sleep(2)
        print(f"Current HVAC Mode (StateManager): {mock_sm.get_value('current_hvac_mode')}")
        print(f"Current Fan State (StateManager): {mock_sm.get_value('current_fan_state')}")
        feedback = get_hvac_feedback()
        print(f"HVAC Feedback: {feedback}")

    else:
        print("Actuator setup failed. Cannot run tests.")
    
    print("\n--- Cleaning up actuators ---")
    cleanup_actuators()
    print("Actuator tests complete.")
