"""Unit tests for Cryptography and Blind Indexing."""

import pytest
from backend.app.core.crypto import encrypt_field, decrypt_field, hmac_hash, compute_audit_hash


def test_encryption_and_decryption_cycle():
    secret_text = "Citizen Phone +91 9823412345"
    encrypted_bytes = encrypt_field(secret_text)
    
    assert encrypted_bytes != b""
    assert isinstance(encrypted_bytes, bytes)
    assert secret_text not in str(encrypted_bytes)

    decrypted = decrypt_field(encrypted_bytes)
    assert decrypted == secret_text


def test_hmac_blind_index_consistency():
    val1 = "fraudster@axisbank"
    val2 = "  FRAUDSTER@AXISBANK  "

    hash1 = hmac_hash(val1)
    hash2 = hmac_hash(val2)

    assert hash1 != ""
    assert hash1 == hash2  # Case-insensitive & trimmed blind indexing


def test_audit_hash_chaining():
    prev = "GENESIS_0"
    payload = {"action": "CASE_CREATED", "ref_no": "SV-001"}
    h1 = compute_audit_hash(prev, payload)
    h2 = compute_audit_hash(prev, payload)

    assert h1 == h2
    assert len(h1) == 64

