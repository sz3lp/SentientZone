from datetime import datetime, timezone, timedelta

from override_handler import OverrideManager
from state_manager import StateManager
from control import HVACController
from tests.mocks.mock_hardware import MockHardwareInterface
from tests.mocks.mock_sensors import MockSensorReader
import state_machine


def create_state(tmpdir):
    config = {
        "pins": {"cooling": 17, "heating": 27, "fan": 22},
        "thresholds": {"cool": 75, "heat": 68},
        "motion_timeout": 300,
        "api_key": "k",
        "use_logic_engine": True,
    }
    state_path = tmpdir / "state.json"
    sm = StateManager(state_path=str(state_path))
    sm.config = config
    return sm


def run_cycle(state, sensors, hvac, override_mgr, now):
    last_motion = state.get("last_motion_ts") or 0
    temp = sensors.temperature
    if temp is not None:
        state.set("last_temp_f", temp)
    if sensors.motion:
        last_motion = now.timestamp()
    state.set("last_motion_ts", last_motion)
    override_mgr.clear_if_expired(now)
    motion_active = now.timestamp() - last_motion < state.config["motion_timeout"]
    override_active = override_mgr.is_override_active(now)
    mode = state_machine.decide(
        temp,
        motion_active,
        state.get("current_mode") or "OFF",
        override_active,
        state.get("override_mode") or "OFF",
        state.config["thresholds"],
    )
    hvac.set_mode(mode)
    state.set("current_mode", mode)


def test_mode_transitions(tmp_path):
    sm = create_state(tmp_path)
    hvac = HVACController(sm.config, hardware=MockHardwareInterface())
    override_mgr = OverrideManager(sm)

    sensors = MockSensorReader(temperature=80.0, motion=True)
    now = datetime.now(timezone.utc)
    run_cycle(sm, sensors, hvac, override_mgr, now)
    assert sm.get("current_mode") == "COOL_ON"

    override_mgr.apply_override("HEAT_ON", 1, "test", "test")
    run_cycle(sm, sensors, hvac, override_mgr, now)
    # immediate transition should enforce idle state
    assert sm.get("current_mode") == "OFF"

    future = now + timedelta(minutes=2)
    run_cycle(sm, sensors, hvac, override_mgr, future)
    assert sm.get("current_mode") == "COOL_ON"

