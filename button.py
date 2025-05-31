# /sz/src/button.py

"""
Module: button.py
Purpose: Detect physical button press and apply local override.
Consumes:
- GPIO input pin configuration from StateManager.
- StateManager to read/write override file path and current mode.
Provides:
- detect_and_apply_override(): triggers override mode toggle.
Behavior:
- On button press, toggles between "manual_on" and "manual_off" by writing to override file.
- Includes a basic debounce delay.
"""

import board
import digitalio
import time
import logging
import pathlib # For robust path handling

# REMOVE THIS LINE: from config_loader import CONFIG
# ADD THIS IMPORT:
from state_manager import StateManager

# Setup module-specific logger
button_logger = logging.getLogger('ButtonHandler')

# --- Global variables for button state and hardware ---
# These will be initialized by the setup_button function
_button_pin_obj = None
_last_button_value = True # Assume button is not pressed initially (pulled high)
_last_toggle_time = 0     # To implement a simple debounce
_debounce_delay_sec = 0.3 # Time to wait after a press before allowing another toggle

# Internal toggle tracker for the override state written by the button
# This should ideally be read from the override file or StateManager directly
# to ensure consistency with other override sources.
# For now, we'll initialize it based on the StateManager's current_mode.
_button_managed_override_state = "manual_off"


def setup_button(state_manager: StateManager):
    """
    Initializes the button hardware based on configuration from StateManager.
    This function should be called once at application startup.

    Args:
        state_manager (StateManager): The application's state manager instance.
    """
    global _button_pin_obj, _button_managed_override_state

    button_bcm_pin = state_manager.get_value('button_gpio_pin') # Assuming a new config key for button pin
    
    # Map BCM GPIO to CircuitPython board pins (re-using mapping from sensor_reader)
    # This mapping should ideally be centralized or consistent across modules.
    BCM_TO_BOARD_PIN = {
        4: board.D4, 5: board.D5, 6: board.D6, 7: board.D7, 8: board.D8,
        9: board.D9, 10: board.D10, 11: board.D11, 12: board.D12, 13: board.D13,
        14: board.D14, 15: board.D15, 16: board.D16, 17: board.D17, 18: board.D18,
        19: board.D19, 20: board.D20, 21: board.D21, 22: board.D22, 23: board.D23,
        24: board.D24, 25: board.D25, 26: board.D26, 27: board.D27,
    }
    button_board_pin = BCM_TO_BOARD_PIN.get(button_bcm_pin)

    if not button_board_pin:
        button_logger.error(f"Button pin (BCM {button_bcm_pin}) not found in board mappings or not configured. Button will not be initialized.")
        return

    try:
        _button_pin_obj = digitalio.DigitalInOut(button_board_pin)
        _button_pin_obj.direction = digitalio.Direction.INPUT
        _button_pin_obj.pull = digitalio.Pull.UP # Assuming pulled high, active low button
        button_logger.info(f"Button initialized on board pin {button_board_pin} (BCM {button_bcm_pin}).")

        # Initialize _button_managed_override_state based on current override file content
        # This ensures the button's internal state matches the actual override.
        # This requires reading the override file, so we'll call get_override_mode from override_manager.
        # **Larger Implementation Note:** This creates a dependency on override_manager.
        # For a truly decoupled system, the button might just signal a "toggle_override" event,
        # and a central override manager would handle the state. For now, this is practical.
        from override_manager import get_override_mode # Import here to avoid circular dependency
        current_override = get_override_mode(state_manager)
        if current_override and current_override.get('mode') in ["manual_on", "manual_off"]:
            _button_managed_override_state = current_override['mode']
            button_logger.info(f"Button handler initialized with current override state: {_button_managed_override_state}")
        else:
            button_logger.info("No active button-managed override found, defaulting to 'manual_off'.")

    except Exception as e:
        button_logger.error(f"Failed to initialize button on board pin {button_board_pin} (BCM {button_bcm_pin}): {e}")
        _button_pin_obj = None # Mark as uninitialized


def detect_and_apply_override(state_manager: StateManager):
    """
    Polls button input and writes override toggle if pressed.
    Should be called once per main loop cycle.

    Args:
        state_manager (StateManager): The application's state manager instance.
    """
    global _last_button_value, _last_toggle_time, _button_managed_override_state

    if not _button_pin_obj: # If button failed to initialize, do nothing
        return

    current_button_value = _button_pin_obj.value # Read current button state

    # Check for a transition from HIGH (unpressed) to LOW (pressed)
    if _last_button_value is True and current_button_value is False: # Button just pressed
        current_time = time.monotonic()
        if (current_time - _last_toggle_time) > _debounce_delay_sec:
            # Debounce passed, process the press
            new_state = "manual_on" if _button_managed_override_state == "manual_off" else "manual_off"
            button_logger.info(f"Button pressed. Toggling override to: {new_state}")

            # Write the new state to the override file
            override_file_path_str = state_manager.get_value('override_file')
            if override_file_path_str:
                override_path = pathlib.Path(override_file_path_str)
                try:
                    override_path.parent.mkdir(parents=True, exist_ok=True)
                    # **Important:** This is a simple file write. For a robust override system,
                    # you'd want to call a function in `override_manager` like `set_override`
                    # which handles timestamps, validation, and potentially signing.
                    # For now, matching original behavior of writing raw text.
                    with open(override_path, "w") as f:
                        f.write(new_state)
                    _button_managed_override_state = new_state # Update internal tracker
                    _last_toggle_time = current_time # Reset debounce timer
                    button_logger.info(f"Override file updated to: {new_state}")
                except IOError as e:
                    button_logger.error(f"Failed to write override file '{override_path}': {e}")
                except Exception as e:
                    button_logger.critical(f"Unexpected error writing override file: {e}", exc_info=True)
            else:
                button_logger.error("Override file path not configured in StateManager. Cannot apply button override.")
        else:
            button_logger.debug("Button press debounced.")

    _last_button_value = current_button_value # Update last state for next loop iteration


def cleanup_button():
    """Clean up GPIO resources for the button."""
    global _button_pin_obj
    if _button_pin_obj:
        try:
            _button_pin_obj.deinit()
            button_logger.info("Button GPIO cleaned up.")
        except Exception as e:
            button_logger.warning(f"Error during button GPIO cleanup: {e}")


# Example Usage for Testing (remove for main integration)
if __name__ == '__main__':
    class MockStateManager:
        def __init__(self):
            self._config = {
                # Ensure this pin matches your actual wiring for testing on a Pi
                'button_gpio_pin': 26, # BCM 26 for board.D26
                'override_file': './test_button_override.txt',
                'current_mode': 'auto' # Initial mode for override_manager to read
            }
            logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            button_logger.setLevel(logging.DEBUG)

            # Mock override_manager.get_override_mode for setup_button
            # This is a bit of a hack for standalone testing, showing dependency.
            global get_override_mode
            def mock_get_override_mode(sm):
                # Simulate reading the override file
                override_file = sm.get_value('override_file')
                if os.path.exists(override_file):
                    try:
                        mode = pathlib.Path(override_file).read_text().strip().lower()
                        if mode in ["manual_on", "manual_off"]:
                            return {'mode': mode, 'end_time': time.time() + 3600} # Mock active override
                    except Exception:
                        pass
                return None
            get_override_mode = mock_get_override_mode # Override the actual import

            # Clean up old test override file
            if os.path.exists(self._config['override_file']):
                os.remove(self._config['override_file'])

        def get_value(self, key, default=None):
            return self._config.get(key, default)

        def set_value(self, key, value, bypass_validation=False):
            self._config[key] = value
            button_logger.debug(f"MockStateManager: Set '{key}' to '{value}'")

    print("--- Testing button.py independently ---")
    mock_sm = MockStateManager()

    # Initialize the button hardware
    setup_button(mock_sm)

    if _button_pin_obj:
        print("\nPress the button (e.g., connect BCM 26 to GND) and release to toggle override.")
        print("Waiting for button presses... (Ctrl+C to exit)")
        
        # Simulate initial state
        override_file = pathlib.Path(mock_sm.get_value('override_file'))
        if override_file.exists():
            initial_state = override_file.read_text().strip()
            print(f"Initial override file state: {initial_state}")
        else:
            print("Override file does not exist initially.")

        try:
            while True:
                detect_and_apply_override(mock_sm)
                time.sleep(0.1) # Small delay to prevent busy-waiting
        except KeyboardInterrupt:
            print("\nExiting button test.")
        finally:
            cleanup_button()
            if os.path.exists(override_file):
                os.remove(override_file)
    else:
        print("\nButton not initialized. Cannot run interactive test. Check pin configuration.")
