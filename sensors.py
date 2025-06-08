"""Sensor interface for SentientZone."""
import time
from logger import get_logger
try:
    import board
    import adafruit_dht
    import RPi.GPIO as GPIO
except Exception:  # pragma: no cover - hardware not present
    board = None
    adafruit_dht = None
    GPIO = None


class SensorManager:
    """Read DHT22 temperature and PIR motion sensors."""

    def __init__(self, config):
        self.logger = get_logger(__name__)
        self.dht_pin = config['pins']['dht']
        self.motion_pin = config['pins']['motion']
        self.dht_device = None
        self.motion = False
        if GPIO:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.motion_pin, GPIO.IN)
        if adafruit_dht:
            board_pin = getattr(board, f'D{self.dht_pin}', None) if board else None
            self.dht_device = adafruit_dht.DHT22(board_pin if board_pin else self.dht_pin)

    def read_temperature(self):
        """Return temperature in Fahrenheit or None."""
        if not self.dht_device:
            return None
        try:
            temp_c = self.dht_device.temperature
            if temp_c is None:
                return None
            return temp_c * 9 / 5 + 32
        except Exception as exc:
            self.logger.error("Temperature read failed: %s", exc)
            return None

    def check_motion(self):
        """Return True if motion detected."""
        if GPIO:
            return GPIO.input(self.motion_pin) == GPIO.HIGH
        return False

    def cleanup(self):
        if GPIO:
            GPIO.cleanup(self.motion_pin)
        if self.dht_device:
            self.dht_device.exit()
