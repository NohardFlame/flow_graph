"""Shared enums and constants.

Minimal placeholders for config and protocols; extended in later phases.
"""

from enum import StrEnum


class RunStatus(StrEnum):
    """Processing run lifecycle (placeholder for Phase 1+)."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class JobStatus(StrEnum):
    """Queue job status (placeholder for Phase 8+)."""

    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    FAILED = "failed"


class PrefilterDecision(StrEnum):
    """Chunk prefilter outcome: keep, gray zone, or reject."""

    KEEP = "keep"
    GRAY = "gray"
    REJECT = "reject"


# Extraction prompt and schema versions (used in cache key and persisted with every result)
EXTRACTION_PROMPT_VERSION = "v1"
EXTRACTION_SCHEMA_VERSION = "v1"
