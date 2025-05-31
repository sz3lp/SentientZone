# /sz/src/watchdog.py

"""
Module: watchdog.py
Purpose: Monitor system health and signal responsiveness.
Consumes:
- StateManager for heartbeat file path.
- Periodic call from main loop.
Provides:
- update_heartbeat(): Writes current UTC timestamp to a file.
Behavior:
- Updates heartbeat file with current UTC timestamp.
- External systemd Watchdog or cron monitors file age to detect unresponsiveness.
"""

from datetime import datetime
import pathlib # For robust path handling
import logging # For logging internal module events/errors

# REMOVE THIS LINE: from config_loader import CONFIG
# ADD THIS IMPORT:
from state_manager import StateManager

# Setup module-specific logger
watchdog_logger = logging.getLogger('Watchdog')


def update_heartbeat(state_manager: StateManager):
    """
    Writes the current UTC timestamp to the heartbeat file.
    This action signals that the system is alive and responsive.

    Args:
        state_manager (StateManager): The application's state manager instance.
    """
    # Get the heartbeat file path from StateManager
    heartbeat_file_str = state_manager.get_value('heartbeat_file')
    if not heartbeat_file_str:
        watchdog_logger.error("Heartbeat file path not configured in StateManager. Cannot update heartbeat.")
        return

    heartbeat_path = pathlib.Path(heartbeat_file_str)
    timestamp = datetime.utcnow().isoformat()

    try:
        # Ensure the parent directory for the heartbeat file exists
        heartbeat_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write the timestamp to the heartbeat file, overwriting previous content
        with open(heartbeat_path, "w") as f:
            f.write(timestamp)
        watchdog_logger.debug(f"Heartbeat updated: {timestamp} to {heartbeat_path}")
    except IOError as e:
        watchdog_logger.error(f"Failed to write heartbeat to '{heartbeat_path}': {e}")
    except Exception as e:
        watchdog_logger.critical(f"An unexpected error occurred updating heartbeat: {e}", exc_info=True)


# Example Usage for Testing (remove for main integration)
if __name__ == '__main__':
    class MockStateManager:
        def __init__(self):
            self._config = {
                'heartbeat_file': './test_heartbeat.txt'
            }
            logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            watchdog_logger.setLevel(logging.DEBUG) # Enable debug for test

            # Clean up old test heartbeat file
            if os.path.exists(self._config['heartbeat_file']):
                os.remove(self._config['heartbeat_file'])
            if not os.path.exists(pathlib.Path(self._config['heartbeat_file']).parent):
                pathlib.Path(self._config['heartbeat_file']).parent.mkdir(parents=True, exist_ok=True)
            watchdog_logger.info(f"Cleaned up old test heartbeat file: {self._config['heartbeat_file']}")

        def get_value(self, key, default=None):
            return self._config.get(key, default)

        def set_value(self, key, value, bypass_validation=False):
            # Not used in this mock for watchdog, but good to have for completeness
            self._config[key] = value

    print("--- Testing watchdog.py independently ---")
    mock_sm = MockStateManager()
    test_heartbeat_path = pathlib.Path(mock_sm.get_value('heartbeat_file'))

    print("\n--- Test 1: Initial heartbeat update ---")
    update_heartbeat(mock_sm)
    time.sleep(0.1) # Give time for file write
    assert test_heartbeat_path.exists()
    content_1 = test_heartbeat_path.read_text().strip()
    print(f"Heartbeat file content: {content_1}")
    assert len(content_1) > 0 # Should contain a timestamp

    print("\n--- Test 2: Subsequent heartbeat update ---")
    time.sleep(0.5) # Simulate time passing
    update_heartbeat(mock_sm)
    content_2 = test_heartbeat_path.read_text().strip()
    print(f"Heartbeat file content: {content_2}")
    assert content_2 > content_1 # New timestamp should be later than old one

    print("\n--- Test 3: Simulate invalid path (should log error) ---")
    mock_sm.set_value('heartbeat_file', '/nonexistent_dir/another_nonexistent_dir/bad_heartbeat.txt')
    update_heartbeat(mock_sm) # This should log an error and not crash

    # Clean up test file
    if test_heartbeat_path.exists():
        os.remove(test_heartbeat_path)
    if pathlib.Path('./test_logs').exists(): # If a test_logs dir was created
        import shutil
        shutil.rmtree('./test_logs')

    print("\nWatchdog tests complete.")
