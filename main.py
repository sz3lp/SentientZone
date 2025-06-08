"""SentientZone entry point."""
import json
import os
import signal
import time
from datetime import datetime, timezone
from pathlib import Path

from sensors import SensorManager
from control import HVACController
from state_manager import StateManager
from server import SentientZoneServer
from button_override import OverrideButton
from override_handler import OverrideManager
from metrics import get_metrics
from logger import get_logger



BASE_DIR = Path(os.environ.get("SZ_BASE_DIR", "/home/pi/sz"))
LOG_PATH = str(BASE_DIR / "logs" / "sentientzone.log")


def main():
    logger = get_logger(__name__)
    state = StateManager()
    sensors = SensorManager(state.config)
    hvac = HVACController(state.config)
    override_mgr = OverrideManager(state)
    server = SentientZoneServer(state, LOG_PATH, override_mgr)
    server.start()
    button = OverrideButton(state.config['pins']['button'], override_mgr)
    button.start()

    metrics = get_metrics()

    running = True

    def handle_signal(sig, frame):
        nonlocal running
        running = False
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    motion_timeout = state.config.get('motion_timeout', 300)
    last_motion = state.get('last_motion_ts') or 0

    while running:
        temp = sensors.read_temperature()
        if temp is not None:
            state.set('last_temp_f', temp)
            metrics.record_temp(temp)
        else:
            metrics.increment_error()
        if sensors.check_motion():
            last_motion = time.time()
        state.set('last_motion_ts', last_motion)

        now = datetime.now(timezone.utc)
        override_mgr.clear_if_expired(now)
        mode = state.get('current_mode', 'OFF')
        if override_mgr.is_override_active(now):
            mode = state.get('override_mode')
        else:
            if temp is None:
                mode = 'OFF'
            elif (
                temp > state.config['thresholds']['cool']
                and time.time() - last_motion < motion_timeout
            ):
                mode = 'COOL_ON'
            elif temp < state.config['thresholds']['heat']:
                mode = 'HEAT_ON'
            else:
                mode = 'FAN_ONLY'
        hvac.set_mode(mode)
        state.set('current_mode', mode)
        metrics.write_metrics(state)
        time.sleep(state.config.get('loop_interval', 5))

    logger.info('Shutting down')
    hvac.set_mode('OFF')
    hvac.cleanup()
    sensors.cleanup()


if __name__ == '__main__':
    main()
