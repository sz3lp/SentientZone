"""Flask API for SentientZone with basic authentication and validation."""

from logger import get_logger
from typing import Any, Dict
import time

from metrics import get_metrics

from flask import Flask, jsonify, request, send_file
from threading import Thread

from override_handler import OverrideManager


class SentientZoneServer(Thread):
    """Simple Flask server running in a thread."""

    def __init__(
        self,
        state_manager,
        log_path: str,
        override_mgr: OverrideManager,
        ifi_reporter: Any | None = None,
    ):
        super().__init__(daemon=True)
        self.state = state_manager
        self.override_mgr = override_mgr
        self.ifi_reporter = ifi_reporter
        self.log_path = log_path
        self.metrics = get_metrics()
        self.app = Flask(__name__)
        self.logger = get_logger(__name__)
        self.api_key = self.state.config.get("api_key")
        self._setup_routes()

    def _setup_routes(self):
        def require_key() -> Any:
            """Validate X-API-Key header for POST requests."""
            key = request.headers.get("X-API-Key")
            if not self.api_key or key != self.api_key:
                self.logger.warning(
                    "Unauthorized request from %s", request.remote_addr
                )
                return jsonify({"error": "unauthorized"}), 401
            return None

        @self.app.route("/state")
        def get_state():
            return jsonify(self.state.state)

        @self.app.route("/override", methods=["POST"])
        def set_override():
            auth_error = require_key()
            if auth_error:
                return auth_error
            try:
                data: Dict[str, Any] = request.get_json(force=True)
            except Exception:
                return jsonify({"error": "invalid json"}), 400
            mode = data.get("mode")
            duration = data.get("duration_minutes")
            source = data.get("source", "api")
            if mode not in {"COOL_ON", "HEAT_ON", "FAN_ONLY", "OFF"}:
                return jsonify({"error": "invalid mode"}), 400
            try:
                duration = int(duration)
            except (TypeError, ValueError):
                return jsonify({"error": "invalid duration"}), 400
            try:
                self.override_mgr.apply_override(
                    mode,
                    duration,
                    source,
                    f"API@{request.remote_addr}",
                )
                self.logger.info(
                    "Override from %s (%s): %s for %s min",
                    request.remote_addr,
                    source,
                    mode,
                    duration,
                )
                return jsonify({
                    "override_mode": self.state.get("override_mode"),
                    "override_until": self.state.get("override_until"),
                })
            except ValueError as exc:
                self.logger.error("Override failed: %s", exc)
                return jsonify({"error": str(exc)}), 400

        @self.app.route("/logs")
        def get_logs():
            return send_file(self.log_path, mimetype="text/plain")

        @self.app.route("/healthz")
        def healthz():
            reasons = []
            now = time.time()
            if not self.state:
                reasons.append("state manager missing")
            if not self.override_mgr:
                reasons.append("override manager missing")
            if self.metrics.last_temp_time is None:
                reasons.append("no temp reading")
            elif now - self.metrics.last_temp_time > 60:
                reasons.append("stale sensor data")
            ok = not reasons
            if not ok:
                self.logger.warning("Health check failed: %s", ", ".join(reasons))
            payload = {
                "status": "ok" if ok else "error",
                "uptime_sec": self.metrics.uptime(),
                "mode": self.state.get("current_mode"),
                "last_temp_f": self.state.get("last_temp_f"),
                "override_active": self.state.get("override_mode") != "OFF",
                "errors": self.metrics.error_count,
            }
            return jsonify(payload), 200 if ok else 503

        @self.app.errorhandler(Exception)
        def handle_exception(exc: Exception):
            self.logger.exception("Unhandled error: %s", exc)
            if self.ifi_reporter:
                try:
                    self.ifi_reporter.log_event(
                        "error",
                        self.state.config.get("device_id", ""),
                        str(exc),
                    )
                except Exception:
                    self.logger.exception("IFI logging failed")
            return jsonify({"error": "internal server error"}), 500

    def run(self):
        self.logger.info("Starting Flask server on 127.0.0.1:8080")
        self.app.run(host="127.0.0.1", port=8080)
