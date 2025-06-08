"""GPIO hardware interface for SentientZone."""
import json
from logger import get_logger
from pathlib import Path

try:
    import RPi.GPIO as GPIO
except Exception:  # pragma: no cover - hardware not present
    GPIO = None


class HardwareInterface:
    """Abstraction layer for HVAC relay control."""

    def __init__(self, config):
        self.logger = get_logger(__name__)
        if isinstance(config, (str, Path)):
            with open(config, 'r') as f:
                config = json.load(f)
        self.pins = {
            'cooling': config['pins']['cooling'],
            'heating': config['pins']['heating'],
            'fan': config['pins']['fan'],
        }
        if GPIO:
            GPIO.setwarnings(False)
            GPIO.setmode(GPIO.BCM)
            try:
                for pin in self.pins.values():
                    GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)
            except Exception as exc:  # pragma: no cover - hardware not present
                self.logger.exception("Failed GPIO setup: %s", exc)

    def activate(self, pin_name: str) -> None:
        """Activate a relay by pin name."""
        pin = self.pins.get(pin_name)
        if pin is None:
            self.logger.error("Unknown pin name: %s", pin_name)
            return
        self.logger.info("Activating %s (GPIO %s)", pin_name, pin)
        if GPIO:
            try:
                GPIO.output(pin, GPIO.HIGH)
            except Exception as exc:  # pragma: no cover - hardware not present
                self.logger.exception("Failed to activate %s: %s", pin_name, exc)

    def deactivate_all(self) -> None:
        """Turn off all relays."""
        self.logger.info("Deactivating all relays")
        if GPIO:
            try:
                for pin in self.pins.values():
                    GPIO.output(pin, GPIO.LOW)
            except Exception as exc:  # pragma: no cover - hardware not present
                self.logger.exception("Failed to deactivate relays: %s", exc)

    def cleanup(self) -> None:
        """Clean up GPIO state."""
        self.logger.info("Cleaning up GPIO")
        if GPIO:
            try:
                GPIO.cleanup(list(self.pins.values()))
            except Exception as exc:  # pragma: no cover - hardware not present
                self.logger.exception("GPIO cleanup failed: %s", exc)
