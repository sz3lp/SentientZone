# /sz/src/config_loader.py

"""
Module: config_loader.py
Purpose: Load and validate system configuration from config.ini.
Consumes: /sz/config/config.ini
Provides: A Config class with immutable access to all system parameters.
Failure Mode: Terminates with error if config is missing or malformed.
This module must be able to regenerate fully and operate standalone.
"""

import configparser
import os
from pathlib import Path


CONFIG_PATH = "/sz/config/config.ini"


class Config:
    def __init__(self):
        self._parser = configparser.ConfigParser()
        self._load_config()
        self._bind_all()

    def _load_config(self):
        if not os.path.isfile(CONFIG_PATH):
            raise FileNotFoundError(f"Config file not found at: {CONFIG_PATH}")
        self._parser.read(CONFIG_PATH)

    def _bind_all(self):
        # --- ZONE_METADATA ---
        self.zone_id = self._get("ZONE_METADATA", "zone_id")
        self.building = self._get("ZONE_METADATA", "building")
        self.room_name = self._get("ZONE_METADATA", "room_name")
        self.climate_zone = self._get("ZONE_METADATA", "climate_zone")
        self.install_date = self._get("ZONE_METADATA", "install_date")
        self.commissioned_by = self._get("ZONE_METADATA", "commissioned_by")

        # --- THRESHOLDS ---
        self.temp_min_comfort = self._get_float("THRESHOLDS", "temp_min_comfort")
        self.temp_max_comfort = self._get_float("THRESHOLDS", "temp_max_comfort")
        self.humid_min_comfort = self._get_float("THRESHOLDS", "humid_min_comfort")
        self.humid_max_comfort = self._get_float("THRESHOLDS", "humid_max_comfort")
        self.motion_timeout_sec = self._get_int("THRESHOLDS", "motion_timeout_sec")
        self.freeze_sensor_window = self._get_int("THRESHOLDS", "freeze_sensor_window")

        # --- ENERGY_MODEL ---
        self.baseline_profile_file = self._get_path("ENERGY_MODEL", "baseline_profile_file")
        self.cost_per_kwh = self._get_float("ENERGY_MODEL", "cost_per_kwh")
        self.co2_per_kwh = self._get_float("ENERGY_MODEL", "co2_per_kwh")
        self.report_hour_utc = self._get_int("ENERGY_MODEL", "report_hour_utc")

        # --- PATHS ---
        self.log_dir = self._get_path("PATHS", "log_dir")
        self.override_file = self._get_path("PATHS", "override_file")
        self.heartbeat_file = self._get_path("PATHS", "heartbeat_file")
        self.key_dir = self._get_path("PATHS", "key_dir")
        self.report_output_dir = self._get_path("PATHS", "report_output_dir")

        # --- RELAY_MAP ---
        self.heat_gpio = self._get_int("RELAY_MAP", "heat_gpio")
        self.cool_gpio = self._get_int("RELAY_MAP", "cool_gpio")
        self.humid_gpio = self._get_int("RELAY_MAP", "humid_gpio")
        self.dehumid_gpio = self._get_int("RELAY_MAP", "dehumid_gpio")

        # --- SAMPLING ---
        self.sensor_interval_sec = self._get_int("SAMPLING", "sensor_interval_sec")
        self.heartbeat_interval_sec = self._get_int("SAMPLING", "heartbeat_interval_sec")
        self.prune_log_days = self._get_int("SAMPLING", "prune_log_days")

        # --- OVERRIDE_SCHEDULE ---
        self.schedule_file = self._get_path("OVERRIDE_SCHEDULE", "schedule_file")
        self.default_mode = self._get("OVERRIDE_SCHEDULE", "default_mode")

        # --- SECURITY ---
        self.node_private_key_file = self._get_path("SECURITY", "node_private_key_file")
        self.signature_algorithm = self._get("SECURITY", "signature_algorithm")
        self.require_signed_override = self._get_bool("SECURITY", "require_signed_override")

        # --- UI ---
        self.ui_host = self._get("UI", "host")
        self.ui_port = self._get_int("UI", "port")
        self.ui_theme = self._get("UI", "ui_theme")

    # Internal retrieval methods
    def _get(self, section, key):
        return self._parser.get(section, key)

    def _get_int(self, section, key):
        return self._parser.getint(section, key)

    def _get_float(self, section, key):
        return self._parser.getfloat(section, key)

    def _get_bool(self, section, key):
        return self._parser.getboolean(section, key)

    def _get_path(self, section, key):
        return Path(self._parser.get(section, key)).expanduser().resolve()


# Global access object
CONFIG = Config()
