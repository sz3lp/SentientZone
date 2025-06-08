class MockHardwareInterface:
    def __init__(self, *args, **kwargs):
        self.actions = []
    def activate(self, pin_name):
        self.actions.append(f"on:{pin_name}")
    def deactivate_all(self):
        self.actions.append("off:all")
    def cleanup(self):
        self.actions.append("cleanup")
