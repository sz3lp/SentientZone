# /sz/src/test_mode.py

"""
Module: test_mode.py
Purpose: Simulate full system behavior with virtual sensor inputs.
Use Case: Development, CI, offline validation
Consumes:
- Predefined test scenarios (list of dicts)
Produces:
- Simulated outputs for sensor_reader, decision_engine, logger
Behavior:
- Emulates sensor_reader.read_sensors()
- Cycles through fake inputs and prints decisions
"""
__test__ = False

import time
from decision_engine import decide_hvac_action
from override_manager import get_override_mode
from logger import get_logger

logger = get_logger(__name__)

# Test scenario: cycle through common input states
TEST_SEQUENCE = [
    {"temperature": 19.5, "humidity": 35.0, "motion": True, "status": "VALID"},
    {"temperature": 25.1, "humidity": 60.0, "motion": True, "status": "VALID"},
    {"temperature": 22.0, "humidity": 40.0, "motion": False, "status": "VALID"},
    {"temperature": None, "humidity": None, "motion": True, "status": "ERROR"},
    {"temperature": 22.0, "humidity": 40.0, "motion": True, "status": "FROZEN"},
]


def run_test_cycle(interval_sec=2):
    """
    Simulates main loop using predefined sensor inputs.
    """
    for fake in TEST_SEQUENCE:
        print("\n--- Simulated Cycle ---")
        override_mode = get_override_mode()
        decision = decide_hvac_action(fake, override_mode)

        logger.info("Sensor: %s", fake)
        logger.info("Decision: %s", decision)

        print(f"Sensor: {fake}")
        print(f"Decision: {decision}")
        time.sleep(interval_sec)
