"""Checksum utilities for storage and ingest."""

import hashlib


def sha256_hex(body: bytes) -> str:
    """Return SHA-256 hash of body as lowercase hex string (64 chars)."""
    return hashlib.sha256(body).hexdigest()
