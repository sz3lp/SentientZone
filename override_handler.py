"""Override management for SentientZone."""

from logger import get_logger
from datetime import datetime, timedelta, timezone
from typing import Any

from audit import log_override

from dateutil import parser

from state_manager import StateManager
from control import VALID_MODES


class OverrideManager:
    """Manage temporary HVAC overrides."""

    def __init__(self, state: StateManager, reporter: Any | None = None) -> None:
        self.state = state
        self.logger = get_logger(__name__)
        self.reporter = reporter

    def is_override_active(self, now: datetime) -> bool:
        """Return True if an override is currently active."""
        mode = self.state.get("override_mode")
        until = self.state.get("override_until")
        if mode and mode != "OFF" and until:
            try:
                expiry = parser.isoparse(until)
                return expiry > now
            except (ValueError, TypeError):
                self.logger.warning("Invalid override_until value: %s", until)
        return False

    def apply_override(
        self,
        mode: str,
        duration_minutes: int,
        source: str,
        initiated_by: str,
    ) -> None:
        """Apply a new override mode for the given duration."""
        if mode not in VALID_MODES:
            self.logger.error("Invalid override mode: %s", mode)
            raise ValueError(f"Invalid mode: {mode}")
        expiry = datetime.now(timezone.utc) + timedelta(minutes=duration_minutes)
        self.state.set("override_mode", mode)
        self.state.set("override_until", expiry.isoformat())
        self.logger.info(
            "Override applied from %s by %s: %s until %s",
            source,
            initiated_by,
            mode,
            expiry.isoformat(),
        )
        log_override(mode, duration_minutes, source, initiated_by)
        if self.reporter:
            try:
                self.reporter.log_event(
                    "override",
                    self.state.config.get("device_id", ""),
                    mode,
                )
            except Exception:
                self.logger.exception("IFI logging failed")

    def clear_if_expired(self, now: datetime) -> None:
        """Clear override if it has expired."""
        until = self.state.get("override_until")
        if not until:
            return
        try:
            expiry = parser.isoparse(until)
        except (ValueError, TypeError):
            self.logger.warning("Invalid override_until value: %s", until)
            self.state.set("override_mode", "OFF")
            self.state.set("override_until", None)
            return
        if expiry <= now:
            self.logger.info("Override expired at %s", until)
            self.state.set("override_mode", "OFF")
            self.state.set("override_until", None)

