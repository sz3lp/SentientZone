from types import SimpleNamespace

import sensors


class DummyDHT:
    def __init__(self, pin):
        self.temperature = 20.0
    def exit(self):
        pass


class DummyGPIO:
    BCM = 1
    IN = 0
    HIGH = 1
    LOW = 0
    def __init__(self):
        self.state = {}
    def setmode(self, mode):
        pass
    def setup(self, pin, mode):
        pass
    def input(self, pin):
        return self.state.get(pin, self.LOW)
    def cleanup(self, pins):
        pass


def test_sensor_reads():
    sensors.adafruit_dht = SimpleNamespace(DHT22=DummyDHT)
    sensors.board = SimpleNamespace(D17="D17")
    gpio = DummyGPIO()
    gpio.state[5] = gpio.HIGH
    sensors.GPIO = gpio
    mgr = sensors.SensorManager({"pins": {"dht": 17, "motion": 5}})
    assert round(mgr.read_temperature(), 1) == 68.0
    assert mgr.check_motion() is True
