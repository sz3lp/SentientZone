# /sz/src/node_identity.py

"""
Module: node_identity.py
Purpose: Load and expose unique cryptographic node identity.
Consumes:
- CONFIG.node_private_key_file
- CONFIG.zone_id, building, room_name
Provides:
- get_node_metadata() → dict with identifying info
- get_private_key() → key object for signing
Behavior:
- Ensures each node has a verifiable identity
- Logs will be signed using this identity
"""

import os
from config_loader import CONFIG
from pathlib import Path

def get_node_metadata():
    """
    Return identifying metadata for this node.
    """
    return {
        "zone_id": CONFIG.zone_id,
        "building": CONFIG.building,
        "room_name": CONFIG.room_name,
        "climate_zone": CONFIG.climate_zone,
    }


def get_private_key_bytes():
    """
    Load and return private key content as bytes.
    """
    key_path = Path(CONFIG.node_private_key_file)
    if not key_path.exists():
        raise FileNotFoundError(f"Private key not found at {key_path}")
    return key_path.read_bytes()
