"""Persistent state manager with validation and recovery."""

import json
from logger import get_logger
import os
import threading
from pathlib import Path
from typing import Any, Dict


class StateManager:
    """Manage configuration and runtime state for SentientZone."""

    DEFAULT_STATE: Dict[str, Any] = {
        "override_mode": "OFF",
        "override_until": None,
        "last_temp_f": None,
        "last_motion_ts": None,
        "current_mode": "OFF",
    }

    def __init__(self, config_path: str = "config/config.json",
                 state_path: str = "state/state.json") -> None:
        self.config_path = Path(config_path)
        self.state_path = Path(state_path)
        self.backup_path = self.state_path.parent / "state_backup.json"
        self._lock = threading.Lock()
        self.logger = get_logger(__name__)
        self.config = self._load_json(self.config_path, {})
        self.state = self._load_state()

    def _load_json(self, path: Path, default: Dict[str, Any]) -> Dict[str, Any]:
        if path.exists():
            try:
                with open(path, "r") as file:
                    return json.load(file)
            except Exception as exc:  # pragma: no cover - file may be corrupted
                self.logger.exception("Failed loading %s: %s", path, exc)
        return default.copy()

    def _load_state(self) -> Dict[str, Any]:
        data = self._load_json(self.state_path, self.DEFAULT_STATE)
        if set(data.keys()) != set(self.DEFAULT_STATE.keys()):
            self.logger.warning("State schema mismatch. Resetting state.")
            data = self.DEFAULT_STATE.copy()
            self._write_state(data)
        return data

    def _write_state(self, data: Dict[str, Any]) -> None:
        tmp_path = self.state_path.with_suffix(".tmp")
        try:
            with open(tmp_path, "w") as tmp_file:
                json.dump(data, tmp_file, indent=4)
            if self.state_path.exists():
                try:
                    with open(self.state_path, "r") as src, open(self.backup_path, "w") as dst:
                        dst.write(src.read())
                except Exception as exc:  # pragma: no cover - file may not exist
                    self.logger.exception("Failed to create backup: %s", exc)
            os.replace(tmp_path, self.state_path)
        except Exception as exc:  # pragma: no cover - disk issues
            self.logger.exception("Failed writing state file: %s", exc)
            if tmp_path.exists():
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

    def save_state(self) -> None:
        """Persist current state atomically with backup."""
        with self._lock:
            self._write_state(self.state)

    def get(self, key: str) -> Any:
        """Thread-safe retrieval of a state value."""
        with self._lock:
            return self.state.get(key)

    def set(self, key: str, value: Any) -> None:
        """Update a state value and persist it."""
        if key not in self.DEFAULT_STATE:
            raise KeyError(f"Unknown state key: {key}")
        with self._lock:
            self.state[key] = value
            self._write_state(self.state)

    def reset_state(self) -> None:
        """Reset state to default values and persist."""
        with self._lock:
            self.state = self.DEFAULT_STATE.copy()
            self._write_state(self.state)
