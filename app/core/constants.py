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
