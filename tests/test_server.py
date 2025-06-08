import json
from pathlib import Path

from server import SentientZoneServer
from state_manager import StateManager
from override_handler import OverrideManager
from metrics import get_metrics, MetricsManager


def create_env(tmpdir):
    config = {
        "pins": {},
        "thresholds": {},
        "api_key": "key",
    }
    config_path = Path(tmpdir) / "config.json"
    state_path = Path(tmpdir) / "state.json"
    with open(config_path, "w") as f:
        json.dump(config, f)
    with open(state_path, "w") as f:
        json.dump(StateManager.DEFAULT_STATE, f)
    sm = StateManager(str(config_path), str(state_path))
    om = OverrideManager(sm)
    MetricsManager.reset_instance()
    metrics = get_metrics(Path(tmpdir) / "metrics.json")
    metrics.record_temp(72.0)
    server = SentientZoneServer(sm, str(Path(tmpdir)/'log.log'), om)
    return sm, om, server, metrics


def test_endpoints(tmp_path):
    sm, om, srv, _ = create_env(tmp_path)
    client = srv.app.test_client()
    res = client.get('/state')
    assert res.status_code == 200
    assert res.get_json()["current_mode"] == "OFF"

    res = client.get('/healthz')
    assert res.status_code == 200

    headers = {"X-API-Key": "key"}
    payload = {"mode": "FAN_ONLY", "duration_minutes": 5}
    res = client.post('/override', json=payload, headers=headers)
    assert res.status_code == 200
    assert sm.get("override_mode") == "FAN_ONLY"

    res = client.post('/override', json=payload, headers={"X-API-Key": "bad"})
    assert res.status_code == 401
