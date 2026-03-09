"""Tests for checksum util. No mocks; assert real SHA-256 values."""

import pytest

from app.core.checksum import sha256_hex


def test_sha256_hex_deterministic():
    body = b"hello"
    assert sha256_hex(body) == sha256_hex(body)
    assert sha256_hex(body) == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"


def test_sha256_hex_empty():
    assert len(sha256_hex(b"")) == 64
    assert sha256_hex(b"") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def test_sha256_hex_lowercase():
    assert sha256_hex(b"x").islower()
    assert sha256_hex(b"x").isalnum()
