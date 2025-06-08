"""Physical button override handler."""
from logger import get_logger
import time
try:
    import RPi.GPIO as GPIO
    from threading import Thread
except Exception:  # pragma: no cover - hardware not present
    GPIO = None
    Thread = object


class OverrideButton(Thread):
    """Monitor a GPIO button for manual override."""

    def __init__(self, pin, override_mgr):
        super().__init__(daemon=True)
        self.pin = pin
        self.override_mgr = override_mgr
        self.logger = get_logger(__name__)
        if GPIO:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def run(self):
        if not GPIO:
            return
        self.logger.info("Listening for override button presses")
        while True:
            if GPIO.input(self.pin) == GPIO.LOW:
                current = self.override_mgr.state.get('override_mode')
                new_mode = 'OFF' if current and current != 'OFF' else 'FAN_ONLY'
                self.override_mgr.apply_override(
                    new_mode,
                    30,
                    'button',
                    'button'
                )
                self.logger.info("Override mode set to %s", new_mode)
                while GPIO.input(self.pin) == GPIO.LOW:
                    pass
            time.sleep(0.1)
