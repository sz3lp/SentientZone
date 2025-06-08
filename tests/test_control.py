from control import HVACController
from tests.mocks.mock_hardware import MockHardwareInterface


def sample_config():
    return {"pins": {"cooling": 17, "heating": 27, "fan": 22}}


def test_set_modes():
    mock_hw = MockHardwareInterface()
    ctrl = HVACController(sample_config(), hardware=mock_hw)
    ctrl.set_mode("COOL_ON")
    assert mock_hw.actions == ["off:all", "on:cooling", "on:fan"]
    mock_hw.actions.clear()
    ctrl.set_mode("COOL_ON")
    assert mock_hw.actions == []
    ctrl.set_mode("HEAT_ON")
    assert mock_hw.actions == ["off:all", "on:heating", "on:fan"]


def test_invalid_mode():
    ctrl = HVACController(sample_config(), hardware=MockHardwareInterface())
    try:
        ctrl.set_mode("BAD")
    except ValueError:
        pass
    else:
        assert False, "Expected ValueError"
