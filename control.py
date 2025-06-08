"""HVAC control logic built on HardwareInterface."""
from logger import get_logger
from typing import Optional

from hardware import HardwareInterface

VALID_MODES = {"COOL_ON", "HEAT_ON", "FAN_ONLY", "OFF"}


class HVACController:
    """Manage HVAC mode transitions."""

    def __init__(self, config, hardware: Optional[HardwareInterface] = None):
        self.logger = get_logger(__name__)
        self.hardware = hardware or HardwareInterface(config)
        self.last_mode = None

    def set_mode(self, mode: str) -> None:
        """Set the HVAC to the requested mode."""
        if mode not in VALID_MODES:
            raise ValueError(f"Invalid mode: {mode}")
        if mode == self.last_mode:
            return
        self.logger.info("Changing mode from %s to %s", self.last_mode, mode)
        if mode == "OFF":
            self.hardware.deactivate_all()
        elif mode == "COOL_ON":
            self.hardware.deactivate_all()
            self.hardware.activate("cooling")
            self.hardware.activate("fan")
        elif mode == "HEAT_ON":
            self.hardware.deactivate_all()
            self.hardware.activate("heating")
            self.hardware.activate("fan")
        elif mode == "FAN_ONLY":
            self.hardware.deactivate_all()
            self.hardware.activate("fan")
        self.last_mode = mode

    def cleanup(self) -> None:
        """Cleanup GPIO resources."""
        self.hardware.cleanup()
