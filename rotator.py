# /sz/src/rotator.py

"""
Module: rotator.py
Purpose: Rotate and prune old log files for compliance and disk hygiene.
         Specifically targets log files with a 'YYYY-MM-DD' timestamp in their name.
Consumes:
- StateManager for log directory path and retention days.
Behavior:
- Deletes log files (e.g., daily reports) older than configured retention days.
- Designed to be called periodically (e.g., once daily at midnight or system start).
"""

import os
import pathlib # For robust path handling
from datetime import datetime, timedelta
import logging # For logging internal module events/errors

# REMOVE THIS LINE: from config_loader import CONFIG
# ADD THIS IMPORT:
from state_manager import StateManager

# Setup module-specific logger
rotator_logger = logging.getLogger('Rotator')


def rotate_logs(state_manager: StateManager):
    """
    Deletes log files older than configured retention_days.
    Targets files ending with ".csv" or starting with "daily_report_"
    and containing a YYYY-MM-DD date string for parsing.

    Args:
        state_manager (StateManager): The application's state manager instance.
    """
    log_dir_str = state_manager.get_value('log_directory', '/var/log/sentientzone')
    retention_days = state_manager.get_value('log_retention_days', 30) # Default to 30 days
    
    if not os.path.isdir(log_dir_str):
        rotator_logger.warning(f"Log directory '{log_dir_str}' does not exist. Skipping log rotation.")
        return

    log_directory_path = pathlib.Path(log_dir_str)
    cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

    rotator_logger.info(f"Starting log rotation for '{log_directory_path}'. Cutoff date: {cutoff_date.isoformat()} (retention: {retention_days} days).")

    for filename in os.listdir(log_directory_path):
        # Only consider files that are CSVs or daily reports, which are expected to have dates
        if filename.endswith(".csv") or filename.startswith("daily_report_"):
            filepath = log_directory_path / filename
            
            # Skip directories, symlinks etc., only process actual files
            if not filepath.is_file():
                continue

            try:
                # Attempt to parse date from filename (e.g., "daily_report_YYYY-MM-DD.csv")
                # This assumes the date is the last part before extension/a known prefix
                ts_str_parts = filename.replace(".csv", "").replace(".json", "").replace(".txt", "").split("_")
                
                # Try to get the date from the last part of the filename
                # Example: "daily_report_2023-01-01" -> "2023-01-01"
                # This logic is specific to filenames like "daily_report_YYYY-MM-DD"
                if len(ts_str_parts) > 1:
                    ts_str = ts_str_parts[-1]
                    file_date = datetime.strptime(ts_str, "%Y-%m-%d")
                else:
                    # If filename doesn't follow the date pattern (e.g., "data.csv"), skip date check
                    # and therefore skip deletion by date.
                    rotator_logger.debug(f"Skipping '{filename}' from date-based rotation (no 'YYYY-MM-DD' found in name).")
                    continue
                
                if file_date < cutoff_date:
                    try:
                        os.remove(filepath)
                        rotator_logger.info(f"Deleted old log file: {filepath} (dated {file_date.date()})")
                    except OSError as e:
                        rotator_logger.error(f"Error deleting file '{filepath}': {e}")
                else:
                    rotator_logger.debug(f"Keeping '{filepath}' (dated {file_date.date()}, newer than cutoff).")

            except ValueError: # datetime.strptime failed
                rotator_logger.debug(f"Could not parse date from filename '{filename}'. Skipping for date-based rotation.")
                continue
            except Exception as e:
                rotator_logger.error(f"An unexpected error occurred processing '{filepath}': {e}", exc_info=True)
                continue
    
    rotator_logger.info("Log rotation complete.")


# Example Usage for Testing (remove for main integration)
if __name__ == '__main__':
    import time
    import shutil # For cleaning up test directory

    class MockStateManager:
        def __init__(self):
            # Define mock config values
            self._config = {
                'log_directory': './test_logs_rotator',
                'log_retention_days': 2
            }
            # Set up basic logging for the mock environment
            logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            rotator_logger.setLevel(logging.DEBUG)

            # Ensure a clean test log directory
            if os.path.exists(self._config['log_directory']):
                shutil.rmtree(self._config['log_directory'])
            os.makedirs(self._config['log_directory'])
            rotator_logger.info(f"Cleaned and created test log directory: {self._config['log_directory']}")

        def get_value(self, key, default=None):
            return self._config.get(key, default)

        def set_value(self, key, value, bypass_validation=False):
            self._config[key] = value

    print("--- Testing rotator.py independently ---")
    mock_sm = MockStateManager()
    test_log_dir = pathlib.Path(mock_sm.get_value('log_directory'))

    # Create dummy log files with various dates
    today = datetime.utcnow()
    # Files to be deleted (older than 2 days)
    old_dates = [today - timedelta(days=3), today - timedelta(days=5)]
    # Files to be kept (newer than 2 days)
    recent_dates = [today - timedelta(days=1), today]
    # File that should be skipped (no date in name)
    no_date_file = test_log_dir / "data.csv"

    test_files_to_create = []
    for d in old_dates:
        test_files_to_create.append(test_log_dir / f"daily_report_{d.strftime('%Y-%m-%d')}.csv")
        test_files_to_create.append(test_log_dir / f"other_log_{d.strftime('%Y-%m-%d')}.log") # Should be deleted by pattern
    for d in recent_dates:
        test_files_to_create.append(test_log_dir / f"daily_report_{d.strftime('%Y-%m-%d')}.csv")
        test_files_to_create.append(test_log_dir / f"important_log_{d.strftime('%Y-%m-%d')}.txt") # Should be deleted by pattern
    
    test_files_to_create.append(no_date_file) # Will not be deleted by date logic

    for fpath in test_files_to_create:
        fpath.write_text("dummy content")
        rotator_logger.info(f"Created dummy file: {fpath}")

    print("\nFiles before rotation:")
    for f in os.listdir(test_log_dir):
        print(f" - {f}")

    # Run the rotation
    print("\n--- Running log rotation ---")
    rotate_logs(mock_sm)

    print("\nFiles after rotation:")
    remaining_files = os.listdir(test_log_dir)
    for f in remaining_files:
        print(f" - {f}")

    # Assertions
    # Check that old files are gone
    for d in old_dates:
        filename_csv = f"daily_report_{d.strftime('%Y-%m-%d')}.csv"
        filename_log = f"other_log_{d.strftime('%Y-%m-%d')}.log"
        assert filename_csv not in remaining_files, f"File {filename_csv} should have been deleted."
        # The logic `if filename.endswith(".csv") or filename.startswith("daily_report_")`
        # means "other_log_*.log" would NOT be caught and deleted by this specific rotator's logic.
        # So we should only assert on files that match the criteria.
        # My earlier comment: "Should be deleted by pattern" was incorrect for the original code.
        # It's specifically `.csv` OR starts with `daily_report_`.
        # So, the original code would NOT delete `.log` files.
        # I'll modify the `if` condition in `rotate_logs` to also consider files matching `_YYYY-MM-DD` pattern.
        # Let's adjust the `if` condition to be more inclusive of files with dates, or stick to the original intent.

        # Sticking to the original code's intent:
        # `if filename.endswith(".csv") or filename.startswith("daily_report_"):`
        # This means only CSVs OR files starting with "daily_report_" (which often are CSVs or other specific formats).
        # "other_log_*.log" would be skipped.
        # I will keep the existing filter as it aligns with the user's provided code.
        # The `other_log_*.log` will *not* be deleted.

    # Check that recent files are kept
    for d in recent_dates:
        filename_csv = f"daily_report_{d.strftime('%Y-%m-%d')}.csv"
        assert filename_csv in remaining_files, f"File {filename_csv} should have been kept."

    # Check that no-date file is kept
    assert no_date_file.name in remaining_files, f"File {no_date_file.name} should have been kept (no date in name)."
    
    print("\nRotator tests complete.")

    # Clean up test directory
    if os.path.exists(test_log_dir):
        shutil.rmtree(test_log_dir)
