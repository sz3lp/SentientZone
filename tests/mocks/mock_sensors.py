class MockSensorReader:
    def __init__(self, temperature=None, motion=False):
        self.temperature = temperature
        self.motion = motion
        self.temp_calls = 0
        self.motion_calls = 0
    def read_temperature(self):
        self.temp_calls += 1
        return self.temperature
    def check_motion(self):
        self.motion_calls += 1
        return self.motion
    def cleanup(self):
        pass
