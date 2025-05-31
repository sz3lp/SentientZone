# /sz/src/crypto_verify.py

"""
Module: crypto_verify.py
Purpose: Verify signed log entries using ed25519 public key.
Consumes:
- Public key (bytes) from provided path
Provides:
- verify_signature(message: str, signature_hex: str, pubkey_bytes: bytes) → bool
Behavior:
- Used during audits or external verification
"""

import nacl.signing
import nacl.exceptions
import nacl.encoding


def verify_signature(message: str, signature_hex: str, pubkey_bytes: bytes) -> bool:
    """
    Verifies a signed message using public key.
    Args:
        message (str): The original message string
        signature_hex (str): Hex-encoded signature
        pubkey_bytes (bytes): Public key in raw format
    Returns:
        bool: True if valid, False otherwise
    """
    try:
        verify_key = nacl.signing.VerifyKey(pubkey_bytes, encoder=nacl.encoding.RawEncoder)
        verify_key.verify(message.encode("utf-8"), bytes.fromhex(signature_hex))
        return True
    except (nacl.exceptions.BadSignatureError, ValueError):
        return False
