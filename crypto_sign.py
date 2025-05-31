# /sz/src/crypto_sign.py

"""
Module: crypto_sign.py
Purpose: Digitally sign log entries using ed25519 private key.
Consumes:
- Private key bytes from node_identity.py
Provides:
- sign_message(message: str) → hex signature
Behavior:
- Stateless signing using cryptographic primitives
- Output is hex-encoded signature for CSV log attachment
"""

import nacl.signing
import nacl.encoding
from node_identity import get_private_key_bytes

# One-time key loader (held in memory)
_private_key = nacl.signing.SigningKey(
    get_private_key_bytes(), encoder=nacl.encoding.RawEncoder
)


def sign_message(message: str) -> str:
    """
    Signs the message string using the private key.
    Args:
        message (str): Any string (e.g. CSV line)
    Returns:
        str: Hex-encoded signature
    """
    signed = _private_key.sign(message.encode("utf-8"))
    return signed.signature.hex()
