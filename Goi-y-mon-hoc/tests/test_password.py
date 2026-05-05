"""Tests cho password hashing và lazy SHA256→bcrypt migration."""
from __future__ import annotations

import hashlib
from backend.main import _hash_password, _verify_password, _is_bcrypt_hash


def test_bcrypt_hash_format():
    h = _hash_password("Test@1234")
    assert _is_bcrypt_hash(h)


def test_bcrypt_verify_correct():
    h = _hash_password("MyPass@99")
    assert _verify_password("MyPass@99", h)


def test_bcrypt_verify_wrong():
    h = _hash_password("MyPass@99")
    assert not _verify_password("WrongPass", h)


def test_sha256_still_accepted():
    """Legacy SHA256 hash phải vẫn được xác thực (lazy migration)."""
    raw = "OldPass@123"
    sha256_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    assert not _is_bcrypt_hash(sha256_hash)
    assert _verify_password(raw, sha256_hash)


def test_sha256_wrong_rejected():
    raw = "OldPass@123"
    sha256_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    assert not _verify_password("WrongPass", sha256_hash)
