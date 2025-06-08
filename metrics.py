"""Metrics tracking for SentientZone."""

import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict

from logger import get_logger


METRICS_FILE = Path("/home/pi/sz/logs/metrics.json")


class MetricsManager:
    """Singleton class managing runtime metrics."""

    _instance = None

    def __new__(cls, path: Path | None = None) -> "MetricsManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init(path or METRICS_FILE)
        return cls._instance

    def _init(self, path: Path) -> None:
        self.path = path
        self.start = time.time()
        self.error_count = 0
        self.last_temp_f: float | None = None
        self.last_temp_time: float | None = None
        self.lock = threading.Lock()
        self.logger = get_logger(__name__)

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (for tests)."""
        cls._instance = None

    def record_temp(self, temp: float) -> None:
        """Record the most recent temperature."""
        with self.lock:
            self.last_temp_f = temp
            self.last_temp_time = time.time()

    def increment_error(self) -> None:
        """Increment error counter."""
        with self.lock:
            self.error_count += 1

    def snapshot(self, state: Any) -> Dict[str, Any]:
        """Return metrics snapshot dict."""
        with self.lock:
            data = {
                "current_mode": state.get("current_mode"),
                "last_temp_f": self.last_temp_f,
                "override_active": state.get("override_mode") != "OFF",
                "uptime_sec": int(time.time() - self.start),
                "error_count": self.error_count,
            }
            return data

    def write_metrics(self, state: Any) -> None:
        """Write metrics snapshot atomically."""
        data = self.snapshot(state)
        tmp = self.path.with_suffix(".tmp")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(tmp, "w") as f:
                json.dump(data, f)
            os.replace(tmp, self.path)
        except Exception as exc:  # pragma: no cover - disk issues
            self.logger.error("Failed to write metrics: %s", exc)
            try:
                tmp.unlink()
            except OSError:
                pass

    def uptime(self) -> int:
        """Return current uptime in seconds."""
        return int(time.time() - self.start)


def get_metrics(path: Path | None = None) -> MetricsManager:
    """Return the singleton metrics manager."""
    return MetricsManager(path)

