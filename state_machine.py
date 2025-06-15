# /sz/src/state_machine.py

"""
Module: state_machine.py
Purpose: Track and enforce legal transitions between HVAC states.
Consumes:
- Requested hvac_state from decision_engine
Provides:
- safe_state_transition(requested_state) → final_state
Behavior:
- Prevents illegal jumps (e.g., COOL_ON → HEAT_ON instantly)
- Enforces idle buffer between opposing states
- Stores internal current_state (volatile)
"""

import time
import logging
import os
from pathlib import Path

_decision_logger: logging.Logger | None = None

def _get_logger() -> logging.Logger:
    global _decision_logger
    if _decision_logger is None:
        base = Path(os.environ.get("SZ_BASE_DIR", "/home/pi/sz"))
        log_path = base / "logs" / "decision.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        logger = logging.getLogger("decision")
        if not logger.handlers:
            handler = logging.FileHandler(log_path)
            handler.setFormatter(logging.Formatter("[%(asctime)s] %(message)s"))
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        _decision_logger = logger
    return _decision_logger

# In-memory state (non-persistent)
_current_state = "OFF"
_last_transition_time = time.time()
_min_idle_time = 10  # seconds between mode reversals


def safe_state_transition(requested_state):
    """
    Ensures legal transitions between HVAC modes.
    Args:
        requested_state (str): Requested state from decision engine
    Returns:
        str: Final state to be executed
    """
    global _current_state, _last_transition_time

    now = time.time()
    opposing = {
        "HEAT_ON": "COOL_ON",
        "COOL_ON": "HEAT_ON"
    }

    # Require cooldown time between opposing modes
    if (requested_state != _current_state and
        opposing.get(requested_state) == _current_state and
        now - _last_transition_time < _min_idle_time):
        return "OFF"  # Enforce neutral idle state

    if requested_state != _current_state:
        _last_transition_time = now
        _current_state = requested_state

    return _current_state


def current_state():
    """
    Returns current internal state.
    """
    return _current_state


def decide(
    temp_f: float | None,
    motion_active: bool,
    current_mode: str,
    override_active: bool,
    override_mode: str,
    thresholds: dict,
) -> str:
    """Determine the desired HVAC mode and enforce state rules."""
    logger = _get_logger()
    if override_active:
        requested = override_mode
    else:
        if temp_f is None:
            requested = "OFF"
        elif temp_f > thresholds.get("cool", 75) and motion_active:
            requested = "COOL_ON"
        elif temp_f < thresholds.get("heat", 68):
            requested = "HEAT_ON"
        else:
            requested = "FAN_ONLY"

    final = safe_state_transition(requested)
    logger.info(
        "temp=%s motion=%s override=%s requested=%s current=%s final=%s",
        temp_f,
        motion_active,
        override_active,
        requested,
        current_mode,
        final,
    )
    return final
