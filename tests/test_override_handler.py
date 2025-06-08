from datetime import datetime, timedelta, timezone
from pathlib import Path
import json

from override_handler import OverrideManager
from state_manager import StateManager


def create_state(tmpdir):
    config_path = Path(tmpdir) / "config.json"
    state_path = Path(tmpdir) / "state.json"
    with open(config_path, "w") as f:
        json.dump({"pins": {}, "thresholds": {}, "api_key": "k"}, f)
    with open(state_path, "w") as f:
        json.dump(StateManager.DEFAULT_STATE, f)
    sm = StateManager(str(config_path), str(state_path))
    return sm


def test_apply_and_active(tmp_path):
    sm = create_state(tmp_path)
    om = OverrideManager(sm)
    om.apply_override("HEAT_ON", 10, "test", "tester")
    assert sm.get("override_mode") == "HEAT_ON"
    assert om.is_override_active(datetime.now(timezone.utc))


def test_invalid_mode(tmp_path):
    sm = create_state(tmp_path)
    om = OverrideManager(sm)
    try:
        om.apply_override("BAD", 5, "test", "tester")
    except ValueError:
        pass
    else:
        assert False, "Expected ValueError"


def test_clear_if_expired(tmp_path):
    sm = create_state(tmp_path)
    om = OverrideManager(sm)
    expiry = datetime.now(timezone.utc) - timedelta(minutes=1)
    sm.set("override_mode", "COOL_ON")
    sm.set("override_until", expiry.isoformat())
    om.clear_if_expired(datetime.now(timezone.utc))
    assert sm.get("override_mode") == "OFF"

