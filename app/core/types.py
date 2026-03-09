"""Shared type aliases and data structures used across the app.

Minimal set for protocol signatures and config; extended in later phases.
"""

from dataclasses import dataclass
from typing import Any

# Identity types used in protocols and repositories
DocumentId = str
RunId = str
ChunkId = str
JobId = str
ActionId = str

# Raw payload from external systems
RawPayload = dict[str, Any]


@dataclass(frozen=True)
class ObjectMetadata:
    """Metadata returned by storage head(); set on upload."""

    size: int
    content_type: str
    metadata: dict[str, str]
