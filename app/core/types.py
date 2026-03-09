"""Shared type aliases used across the app.

Minimal set for protocol signatures and config; extended in later phases.
"""

from typing import Any

# Identity types used in protocols and repositories
DocumentId = str
RunId = str
ChunkId = str
JobId = str
ActionId = str

# Raw payload from external systems
RawPayload = dict[str, Any]
