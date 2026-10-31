"""SurakshaVani Cryptography & Blind Indexing Engine.

Implements AES-256-GCM application-layer field encryption and HMAC-SHA256
blind indexing for DPDP Act 2023 compliance.
"""

import base64
import hashlib
import hmac
import json
import os
from typing import Any, Dict
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from backend.app.config import settings

# 32 bytes derived key for AES-256-GCM
_RAW_KEY = hashlib.sha256(settings.FIELD_ENCRYPTION_KEY.encode()).digest()
_AES_GCM = AESGCM(_RAW_KEY)


def encrypt_field(plaintext: str) -> bytes:
    """Encrypts plaintext string using AES-256-GCM with a random 96-bit nonce."""
    if not plaintext:
        return b""
    nonce = os.urandom(12)  # 96-bit nonce
    ciphertext = _AES_GCM.encrypt(nonce, plaintext.encode("utf-8"), None)
    # Store nonce prepended to ciphertext
    return nonce + ciphertext


def decrypt_field(cipher_data: bytes) -> str:
    """Decrypts AES-256-GCM encrypted byte sequence."""
    if not cipher_data:
        return ""
    if len(cipher_data) < 13:
        return ""
    nonce = cipher_data[:12]
    ciphertext = cipher_data[12:]
    try:
        decrypted_bytes = _AES_GCM.decrypt(nonce, ciphertext, None)
        return decrypted_bytes.decode("utf-8")
    except Exception:
        return "[ENCRYPTED_PII_CORRUPTED]"


def hmac_hash(value: str) -> str:
    """Computes deterministic HMAC-SHA256 hash using the secret pepper for blind indexing."""
    if not value:
        return ""
    normalized = value.strip().lower()
    return hmac.new(
        settings.HMAC_PEPPER.encode("utf-8"),
        normalized.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()


def compute_audit_hash(prev_hash: str, entry_dict: Dict[str, Any]) -> str:
    """Computes tamper-evident SHA-256 hash chaining for audit logs."""
    serialized = json.dumps(entry_dict, sort_keys=True)
    combined = f"{prev_hash}:{serialized}"
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()
