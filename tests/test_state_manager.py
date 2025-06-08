import json
from pathlib import Path

from state_manager import StateManager


def create_paths(tmpdir):
    config = {
        "pins": {"dht": 4, "motion": 5, "cooling": 17, "heating": 27, "fan": 22, "button": 6},
        "thresholds": {"cool": 75, "heat": 68},
        "loop_interval": 5,
        "motion_timeout": 300,
        "api_key": "key",
    }
    config_path = Path(tmpdir) / "config.json"
    state_path = Path(tmpdir) / "state.json"
    with open(config_path, "w") as f:
        json.dump(config, f)
    with open(state_path, "w") as f:
        json.dump(StateManager.DEFAULT_STATE, f)
    return config_path, state_path


def test_load_valid_state(tmp_path):
    config_path, state_path = create_paths(tmp_path)
    sm = StateManager(str(config_path), str(state_path))
    assert sm.state == StateManager.DEFAULT_STATE


def test_corrupted_state_file(tmp_path):
    config_path, state_path = create_paths(tmp_path)
    state_path.write_text("{bad json}")
    sm = StateManager(str(config_path), str(state_path))
    assert sm.state == StateManager.DEFAULT_STATE


def test_schema_mismatch_resets(tmp_path):
    config_path, state_path = create_paths(tmp_path)
    with open(state_path, "w") as f:
        json.dump({"bad": 1}, f)
    sm = StateManager(str(config_path), str(state_path))
    assert sm.state == StateManager.DEFAULT_STATE


def test_atomic_save_and_backup(tmp_path):
    config_path, state_path = create_paths(tmp_path)
    sm = StateManager(str(config_path), str(state_path))
    sm.set("current_mode", "COOL_ON")
    backup = Path(tmp_path) / "state_backup.json"
    assert state_path.exists()
    assert backup.exists()
    with open(state_path) as f:
        data = json.load(f)
    assert data["current_mode"] == "COOL_ON"
