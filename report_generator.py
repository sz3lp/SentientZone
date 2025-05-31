# /sz/src/report_generator.py

"""
Module: report_generator.py
Purpose: Generate daily summary reports from historical log data.
Consumes:
- Log files (e.g., sensor_data.csv, hvac_decisions.csv) from log_directory.
- StateManager for log directory and report file path.
Produces:
- Daily summary CSV reports (e.g., daily_report_YYYY-MM-DD.csv).
Behavior:
- Calculates daily averages for temp/humidity, summarizes HVAC states.
- Designed to be called once daily (e.g., at a specific UTC hour).
"""

import csv
import os
import pathlib # For robust path handling
from datetime import datetime, timedelta
import logging

# ADD THIS IMPORT:
from state_manager import StateManager

# Setup module-specific logger
report_logger = logging.getLogger('ReportGenerator')

# Define headers for the daily report CSV
DAILY_REPORT_HEADERS = [
    "date",
    "avg_temperature_c",
    "min_temperature_c",
    "max_temperature_c",
    "avg_humidity",
    "min_humidity",
    "max_humidity",
    "motion_detected_count",
    "hvac_on_duration_minutes",
    "hvac_mode_auto_duration_minutes",
    "hvac_mode_manual_on_duration_minutes",
    "hvac_mode_manual_off_duration_minutes",
    "report_generated_timestamp_utc"
]

def generate_daily_report(state_manager: StateManager):
    """
    Generates a daily summary report for the previous day.
    Reads sensor and HVAC decision logs to compile the report.

    Args:
        state_manager (StateManager): The application's state manager instance.
    """
    log_dir_str = state_manager.get_value('log_directory', '/var/log/sentientzone')
    sensor_log_filename = state_manager.get_value('sensor_log_file', 'sensor_data.csv')
    hvac_log_filename = state_manager.get_value('hvac_log_file', 'hvac_decisions.csv')
    report_file_prefix = state_manager.get_value('daily_report_prefix', 'daily_report')

    if not os.path.isdir(log_dir_str):
        report_logger.warning(f"Log directory '{log_dir_str}' does not exist. Cannot generate daily report.")
        return

    # Calculate the date for the report (yesterday, assuming report runs at midnight today)
    report_date = datetime.utcnow() - timedelta(days=1)
    report_date_str = report_date.strftime("%Y-%m-%d")
    report_timestamp_utc = datetime.utcnow().isoformat()

    report_logger.info(f"Generating daily report for: {report_date_str}")

    sensor_log_path = pathlib.Path(log_dir_str) / sensor_log_filename
    hvac_log_path = pathlib.Path(log_dir_str) / hvac_log_filename
    
    # Initialize data aggregators
    temperatures = []
    humidities = []
    motion_detected_count = 0
    hvac_state_durations = {
        "ON": 0, "OFF": 0, "HEAT_ON": 0, "COOL_ON": 0, "FAN_ON": 0
    }
    hvac_mode_durations = {
        "AUTO": 0, "manual_on": 0, "manual_off": 0
    }
    
    last_hvac_timestamp = None
    last_hvac_state = None
    last_hvac_mode = None

    # --- Process Sensor Data ---
    if sensor_log_path.exists():
        try:
            with open(sensor_log_path, 'r', newline='') as f:
                reader = csv.DictReader(f, fieldnames=["timestamp", "temperature", "humidity", "pressure_hpa", "motion", "status"])
                # Skip header if present (assuming logger.py writes headers)
                first_line = f.readline().strip()
                if first_line.startswith("timestamp"): # Check if it's the header line
                     f.seek(0) # Reset file pointer
                     next(reader) # Skip header
                
                for row in reader:
                    try:
                        entry_date = datetime.fromisoformat(row['timestamp']).date()
                        if entry_date == report_date.date():
                            if row.get('temperature') is not None and row.get('temperature') != 'None':
                                temperatures.append(float(row['temperature']))
                            if row.get('humidity') is not None and row.get('humidity') != 'None':
                                humidities.append(float(row['humidity']))
                            if row.get('motion') == '1': # Assuming '1' for detected
                                motion_detected_count += 1
                    except (ValueError, KeyError) as e:
                        report_logger.warning(f"Skipping malformed sensor log row: {row} - Error: {e}")
        except FileNotFoundError:
            report_logger.warning(f"Sensor log file '{sensor_log_path}' not found for report generation.")
        except Exception as e:
            report_logger.error(f"Error reading sensor log file '{sensor_log_path}': {e}", exc_info=True)
    else:
        report_logger.info(f"Sensor log file '{sensor_log_path}' does not exist, skipping sensor data aggregation.")


    # --- Process HVAC Decision Data ---
    if hvac_log_path.exists():
        try:
            with open(hvac_log_path, 'r', newline='') as f:
                reader = csv.DictReader(f, fieldnames=["timestamp", "hvac_state", "mode", "cause", "current_temp_c", "current_humidity", "current_effective_target_temp_c"])
                # Skip header if present
                first_line = f.readline().strip()
                if first_line.startswith("timestamp"): # Check if it's the header line
                     f.seek(0) # Reset file pointer
                     next(reader) # Skip header

                for row in reader:
                    try:
                        current_hvac_timestamp = datetime.fromisoformat(row['timestamp'])
                        if current_hvac_timestamp.date() == report_date.date():
                            current_hvac_state = row.get('hvac_state')
                            current_hvac_mode = row.get('mode')

                            if last_hvac_timestamp and last_hvac_state and last_hvac_mode:
                                duration = (current_hvac_timestamp - last_hvac_timestamp).total_seconds() / 60 # In minutes

                                if last_hvac_state in hvac_state_durations:
                                    hvac_state_durations[last_hvac_state] += duration
                                if last_hvac_mode in hvac_mode_durations:
                                    hvac_mode_durations[last_hvac_mode] += duration
                                else:
                                    # Catch any unexpected modes
                                    hvac_mode_durations['AUTO'] += duration # Default to auto if unhandled

                            last_hvac_timestamp = current_hvac_timestamp
                            last_hvac_state = current_hvac_state
                            last_hvac_mode = current_hvac_mode
                        elif current_hvac_timestamp.date() > report_date.date():
                            # If we've passed the report date, stop processing for efficiency
                            break
                    except (ValueError, KeyError) as e:
                        report_logger.warning(f"Skipping malformed HVAC log row: {row} - Error: {e}")
        except FileNotFoundError:
            report_logger.warning(f"HVAC decision log file '{hvac_log_path}' not found for report generation.")
        except Exception as e:
            report_logger.error(f"Error reading HVAC decision log file '{hvac_log_path}': {e}", exc_info=True)
    else:
        report_logger.info(f"HVAC decision log file '{hvac_log_path}' does not exist, skipping HVAC aggregation.")

    # --- Compile Report Data ---
    avg_temp = round(sum(temperatures) / len(temperatures), 2) if temperatures else None
    min_temp = round(min(temperatures), 2) if temperatures else None
    max_temp = round(max(temperatures), 2) if temperatures else None
    avg_humid = round(sum(humidities) / len(humidities), 2) if humidities else None
    min_humid = round(min(humidities), 2) if humidities else None
    max_humid = round(max(humidities), 2) if humidities else None

    # Total duration for ON states (HEAT_ON, COOL_ON, FAN_ON implies "ON" for HVAC)
    hvac_on_total_minutes = sum([hvac_state_durations.get(s, 0) for s in ["ON", "HEAT_ON", "COOL_ON", "FAN_ON"]])

    report_data = {
        "date": report_date_str,
        "avg_temperature_c": avg_temp,
        "min_temperature_c": min_temp,
        "max_temperature_c": max_temp,
        "avg_humidity": avg_humid,
        "min_humidity": min_humid,
        "max_humidity": max_humid,
        "motion_detected_count": motion_detected_count,
        "hvac_on_duration_minutes": round(hvac_on_total_minutes, 2),
        "hvac_mode_auto_duration_minutes": round(hvac_mode_durations.get("AUTO", 0), 2),
        "hvac_mode_manual_on_duration_minutes": round(hvac_mode_durations.get("manual_on", 0), 2),
        "hvac_mode_manual_off_duration_minutes": round(hvac_mode_durations.get("manual_off", 0), 2),
        "report_generated_timestamp_utc": report_timestamp_utc
    }

    # --- Write Report to CSV ---
    report_filename = f"{report_file_prefix}_{report_date_str}.csv"
    report_filepath = pathlib.Path(log_dir_str) / report_filename

    try:
        report_filepath.parent.mkdir(parents=True, exist_ok=True)
        file_exists = report_filepath.exists()

        with open(report_filepath, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=DAILY_REPORT_HEADERS)
            if not file_exists:
                writer.writeheader()
                report_logger.info(f"Created new daily report file and wrote headers: {report_filepath}")
            writer.writerow(report_data)
        report_logger.info(f"Successfully generated daily report for {report_date_str} at {report_filepath}")

    except IOError as e:
        report_logger.error(f"Failed to write daily report to '{report_filepath}': {e}")
    except Exception as e:
        report_logger.critical(f"An unexpected error occurred writing daily report: {e}", exc_info=True)


# Example Usage for Testing (remove for main integration)
if __name__ == '__main__':
    import shutil
    import os
    import time # Needed for sleep

    class MockStateManager:
        def __init__(self):
            self._config = {
                'log_directory': './test_reports',
                'sensor_log_file': 'sensor_data.csv',
                'hvac_log_file': 'hvac_decisions.csv',
                'daily_report_prefix': 'my_daily_summary',
                'report_hour_utc': 0 # Not used by generator directly, but part of config
            }
            logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            report_logger.setLevel(logging.DEBUG)

            # Clean up old test directory
            if os.path.exists(self._config['log_directory']):
                shutil.rmtree(self._config['log_directory'])
            os.makedirs(self._config['log_directory'])
            report_logger.info(f"Cleaned and created test log directory: {self._config['log_directory']}")

        def get_value(self, key, default=None):
            return self._config.get(key, default)

        def set_value(self, key, value, bypass_validation=False):
            self._config[key] = value

    print("--- Testing report_generator.py independently ---")
    mock_sm = MockStateManager()
    test_log_dir = pathlib.Path(mock_sm.get_value('log_directory'))
    sensor_log_path = test_log_dir / mock_sm.get_value('sensor_log_file')
    hvac_log_path = test_log_dir / mock_sm.get_value('hvac_log_file')

    # Create dummy log files for yesterday's data
    yesterday = datetime.utcnow() - timedelta(days=1)
    
    # Dummy sensor data for yesterday
    with open(sensor_log_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "temperature", "humidity", "pressure_hpa", "motion", "status"]) # Headers
        # Hourly data points for yesterday
        for hour in range(24):
            ts = yesterday.replace(hour=hour, minute=0, second=0, microsecond=0)
            writer.writerow([
                ts.isoformat(),
                f"{20 + hour * 0.1:.2f}",  # Temp changes
                f"{40 + hour * 0.5:.2f}",  # Humidity changes
                "1012.0",
                "1" if hour % 3 == 0 else "0", # Motion every 3 hours
                "VALID"
            ])
    report_logger.info(f"Created dummy sensor log: {sensor_log_path}")

    # Dummy HVAC decision data for yesterday
    with open(hvac_log_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "hvac_state", "mode", "cause", "current_temp_c", "current_humidity", "current_effective_target_temp_c"]) # Headers
        # HVAC state changes
        for i in range(1, 24):
            ts = yesterday.replace(hour=i, minute=0, second=0, microsecond=0)
            state = "HEAT_ON" if i % 4 == 0 else ("COOL_ON" if i % 4 == 1 else "OFF")
            mode = "manual_on" if i % 7 == 0 else ("manual_off" if i % 7 == 1 else "AUTO")
            writer.writerow([
                ts.isoformat(),
                state,
                mode,
                f"test_cause_{i}",
                f"{20 + i * 0.1:.2f}",
                f"{40 + i * 0.5:.2f}",
                "21.0"
            ])
    report_logger.info(f"Created dummy HVAC log: {hvac_log_path}")

    # Generate the report
    print("\n--- Generating daily report ---")
    generate_daily_report(mock_sm)

    # Verify the report file was created
    report_filename_expected = f"{mock_sm.get_value('daily_report_prefix')}_{yesterday.strftime('%Y-%m-%d')}.csv"
    report_filepath_expected = test_log_dir / report_filename_expected

    if report_filepath_expected.exists():
        print(f"\nReport file created: {report_filepath_expected}")
        print("\nContents of generated report:")
        with open(report_filepath_expected, 'r') as f:
            print(f.read())
    else:
        print(f"\nERROR: Report file was NOT created at {report_filepath_expected}")

    # Clean up test directory
    if os.path.exists(test_log_dir):
        shutil.rmtree(test_log_dir)
    print("\nReport generator tests complete.")
