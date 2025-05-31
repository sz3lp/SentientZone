# /sz/src/energy_model.py

"""
Module: energy_model.py
Purpose: Track and compute energy usage for HVAC actions vs. baseline.
Consumes:
- hvac_state decisions from decision_engine.py
- CONFIG.cost_per_kwh, CONFIG.co2_per_kwh
- CONFIG.baseline_profile_file
Produces:
- Aggregated runtime values for daily reporting
- Energy/cost/co2 savings vs. always-on baseline model
"""

import json
from config_loader import CONFIG

# Internal counters (reset daily)
_runtime_seconds = {
    "HEAT_ON": 0,
    "COOL_ON": 0,
    "FAN_ONLY": 0,
    "OFF": 0
}


def record_runtime(hvac_state, interval_seconds):
    """
    Increment runtime counter for current hvac_state.
    """
    if hvac_state in _runtime_seconds:
        _runtime_seconds[hvac_state] += interval_seconds


def get_runtime_summary():
    """
    Return current runtime summary as a dict.
    Used by report_generator.py
    """
    return _runtime_seconds.copy()


def compute_savings():
    """
    Compare current runtime to always-on baseline profile.
    Returns energy_saved_kwh, cost_saved_usd, co2_saved_kg
    """
    try:
        with open(CONFIG.baseline_profile_file, "r") as f:
            baseline = json.load(f)
    except Exception:
        return {"kwh_saved": 0.0, "usd_saved": 0.0, "co2_saved": 0.0}

    actual_seconds = _runtime_seconds["HEAT_ON"] + _runtime_seconds["COOL_ON"]
    baseline_seconds = baseline.get("daily_seconds", 86400)

    if actual_seconds >= baseline_seconds:
        return {"kwh_saved": 0.0, "usd_saved": 0.0, "co2_saved": 0.0}

    delta_hours = (baseline_seconds - actual_seconds) / 3600.0
    kwh_saved = delta_hours  # Assume 1kWh per hour runtime baseline
    usd_saved = kwh_saved * CONFIG.cost_per_kwh
    co2_saved = kwh_saved * CONFIG.co2_per_kwh

    return {
        "kwh_saved": round(kwh_saved, 3),
        "usd_saved": round(usd_saved, 2),
        "co2_saved": round(co2_saved, 3)
    }


def reset_counters():
    """
    Reset all runtime counters (called at 23:59).
    """
    for key in _runtime_seconds:
        _runtime_seconds[key] = 0
