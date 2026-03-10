"""Shared enums and constants.

Minimal placeholders for config and protocols; extended in later phases.
"""

from enum import StrEnum


class RunStatus(StrEnum):
    """Processing run lifecycle. Aligns with PublicRunStatus for API."""

    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    PARTIAL_SUCCESS = "partial_success"
    CANCELLED = "cancelled"


# Ordered pipeline steps for run orchestration (Phase 8). Each step is callable independently for resume/debug.
RUN_PIPELINE_STEPS = (
    "ingest_ready",
    "parse_document",
    "build_chunks",
    "prefilter_chunks",
    "extract_actions",
    "normalize_actions",
    "persist_results",
    "optional_index",
    "complete_run",
)


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
EXTRACTION_SCHEMA_VERSION = "1.1"  # action_draft_v1_1
