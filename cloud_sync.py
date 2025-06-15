"""Background cloud synchronization for SentientZone."""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

import logging

try:
    import requests
except Exception:  # pragma: no cover - requests may not be installed in tests
    requests = None  # type: ignore



class CloudSync(threading.Thread):
    """Periodically sync state to the SentientZone cloud."""

    def __init__(self, state_manager: Any, interval: int = 60) -> None:
        super().__init__(daemon=True)
        self.state = state_manager
        self.interval = interval
        self.running = True
        base = Path(os.environ.get("SZ_BASE_DIR", "/home/pi/sz"))
        self.buffer_path = base / "logs" / "cloud_buffer.json"
        self.log_path = base / "logs" / "cloud_sync.log"
        self.logger = self._setup_logger()
        self.queue = self._load_queue()
        self.cloud_url: Optional[str] = self.state.config.get("cloud_url")
        self.pull_url: Optional[str] = self.state.config.get("pull_config_url")

    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger("cloud_sync")
        if not logger.handlers:
            logger.setLevel(logging.INFO)
            handler = logging.FileHandler(self.log_path)
            handler.setFormatter(
                logging.Formatter("[%(asctime)s] %(levelname)s %(message)s")
            )
            logger.addHandler(handler)
        return logger

    def _load_queue(self) -> list[Dict[str, Any]]:
        if self.buffer_path.exists():
            try:
                with open(self.buffer_path, "r") as f:
                    return json.load(f)
            except Exception:
                self.logger.warning("Failed reading buffer file; starting empty")
        return []

    def _save_queue(self) -> None:
        try:
            self.buffer_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.buffer_path, "w") as f:
                json.dump(self.queue, f)
        except Exception as exc:
            self.logger.error("Failed saving buffer: %s", exc)

    def stop(self) -> None:
        self.running = False

    def build_payload(self) -> Dict[str, Any]:
        now = time.time()
        last_motion = self.state.get("last_motion_ts") or 0
        motion_timeout = self.state.config.get("motion_timeout", 300)
        motion_active = now - last_motion < motion_timeout
        payload = {
            "timestamp": int(now),
            "temperature_f": self.state.get("last_temp_f"),
            "motion": motion_active,
            "mode": self.state.get("current_mode"),
        }
        return payload

    def _post_payload(self, payload: Dict[str, Any]) -> bool:
        if not requests or not self.cloud_url:
            return False
        for attempt in range(3):
            try:
                r = requests.post(self.cloud_url, json=payload, timeout=5)
                if r.status_code == 200:
                    return True
                self.logger.warning(
                    "POST failed (%s): status %s", attempt + 1, r.status_code
                )
            except Exception as exc:  # pragma: no cover - network issues
                self.logger.warning("POST failed (%s): %s", attempt + 1, exc)
            time.sleep(1)
        return False

    def _pull_config(self) -> None:
        if not requests or not self.pull_url:
            return
        try:
            r = requests.get(self.pull_url, timeout=5)
            if r.status_code == 200:
                data = r.json()
                with open(self.state.config_path, "w") as f:
                    json.dump(data, f, indent=4)
                self.state.config.update(data)
                self.logger.info("Config updated from cloud")
            else:
                self.logger.warning("Config pull failed: status %s", r.status_code)
        except Exception as exc:  # pragma: no cover - network issues
            self.logger.warning("Config pull failed: %s", exc)

    def run(self) -> None:
        self.logger.info("Cloud sync thread started")
        while self.running:
            payload = self.build_payload()
            self.queue.append(payload)
            self._save_queue()
            while self.queue:
                if self._post_payload(self.queue[0]):
                    self.queue.pop(0)
                    self._save_queue()
                else:
                    break
            self._pull_config()
            time.sleep(self.interval)
        self.logger.info("Cloud sync thread stopped")
