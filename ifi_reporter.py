"""IFI telemetry reporting for SentientZone."""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import requests
except Exception:  # pragma: no cover - requests may be missing in tests
    requests = None  # type: ignore

from logger import get_logger
from metrics import get_metrics


class IFIReporter:
    """Send telemetry events to the IFI backend."""

    def __init__(self, state_manager: Any) -> None:
        self.state = state_manager
        base = Path(os.environ.get("SZ_BASE_DIR", "/home/pi/sz"))
        self.queue_path = base / "logs" / "ifi_queue.json"
        self.logger = get_logger(__name__)
        self.queue = self._load_queue()
        self.url: Optional[str] = self.state.config.get("ifi_url")
        self.device_id: Optional[str] = self.state.config.get("device_id")

    def _load_queue(self) -> list[Dict[str, Any]]:
        if self.queue_path.exists():
            try:
                with open(self.queue_path, "r") as f:
                    return json.load(f)
            except Exception:
                self.logger.warning("Failed reading IFI queue; starting empty")
        return []

    def _save_queue(self) -> None:
        try:
            self.queue_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.queue_path, "w") as f:
                json.dump(self.queue, f)
        except Exception as exc:
            self.logger.error("Failed saving IFI queue: %s", exc)

    def _post(self, payload: Dict[str, Any]) -> bool:
        if not requests or not self.url:
            return False
        for attempt in range(3):
            try:
                r = requests.post(self.url, json=payload, timeout=5)
                if r.status_code == 200:
                    return True
                self.logger.warning(
                    "IFI POST failed (%s): status %s", attempt + 1, r.status_code
                )
            except Exception as exc:  # pragma: no cover - network issues
                self.logger.warning("IFI POST failed (%s): %s", attempt + 1, exc)
            time.sleep(1)
        return False

    def _send_or_queue(self, payload: Dict[str, Any]) -> None:
        if self._post(payload):
            return
        self.queue.append(payload)
        self._save_queue()

    def flush_queue(self) -> None:
        while self.queue:
            if self._post(self.queue[0]):
                self.queue.pop(0)
                self._save_queue()
            else:
                break

    def boot_report(self) -> None:
        if not self.url:
            return
        payload = {
            "device_id": self.device_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": "boot",
            "uptime_sec": get_metrics().uptime(),
            "error_count": get_metrics().error_count,
        }
        self.flush_queue()
        self._send_or_queue(payload)

    def log_event(self, event_type: str, zone_id: str, value: Any) -> None:
        if not self.url:
            return
        payload = {
            "device_id": self.device_id,
            "zone_id": zone_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "value": value,
        }
        self.flush_queue()
        self._send_or_queue(payload)
