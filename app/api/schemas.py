"""Pydantic request/response schemas and public API enums. No ORM in responses."""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class PublicRunStatus(StrEnum):
    """Public run status contract. Internal worker step names are not exposed."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    PARTIAL_SUCCESS = "partial_success"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


# Map internal DB status to public API status (single place)
_INTERNAL_TO_PUBLIC: dict[str, PublicRunStatus] = {
    "pending": PublicRunStatus.QUEUED,
    "queued": PublicRunStatus.QUEUED,
    "running": PublicRunStatus.RUNNING,
    "completed": PublicRunStatus.SUCCEEDED,
    "succeeded": PublicRunStatus.SUCCEEDED,
    "failed": PublicRunStatus.FAILED,
    "partial_success": PublicRunStatus.PARTIAL_SUCCESS,
    "partial": PublicRunStatus.PARTIAL_SUCCESS,
    "cancelled": PublicRunStatus.CANCELLED,
}


def internal_status_to_public(internal_status: str) -> PublicRunStatus:
    """Map internal Run.status to public API enum."""
    return _INTERNAL_TO_PUBLIC.get(
        (internal_status or "").strip().lower(), PublicRunStatus.UNKNOWN
    )


# --- Document ---


class DocumentResponse(BaseModel):
    id: str
    original_filename: str
    content_type: str
    size_bytes: int
    created_at: datetime


class DocumentCreatedResponse(BaseModel):
    id: str
    original_filename: str
    content_type: str
    size_bytes: int


# --- Run ---


class RunResponse(BaseModel):
    id: str
    document_id: str
    status: PublicRunStatus
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error_message: str | None = None
    error_code: str | None = None
    current_step: str | None = None


class RunCreatedResponse(BaseModel):
    id: str
    document_id: str


class RunEventItem(BaseModel):
    step: str
    event_type: str
    created_at: datetime
    payload: dict[str, Any] | None = None


class RunEventsResponse(BaseModel):
    items: list[RunEventItem]


# --- Chunks (paginated) ---


class ChunkItem(BaseModel):
    id: str
    chunk_hash: str
    text: str
    estimated_tokens: int | None = None
    prefilter_decision: str | None = None


class ChunkListResponse(BaseModel):
    items: list[ChunkItem]
    total: int
    limit: int
    offset: int


# --- Actions (paginated) ---


class ActionItem(BaseModel):
    id: str
    action_label: str
    action_canonical: str
    confidence: float | None = None
    primary_actor_key: str | None = None
    primary_object_key: str | None = None
    input_state_key: str | None = None
    output_state_key: str | None = None


class ActionListResponse(BaseModel):
    items: list[ActionItem]
    total: int
    limit: int
    offset: int


class RunGraphResponse(BaseModel):
    """All actions for a run (no pagination), for graph visualization."""

    run_id: str
    items: list[ActionItem]


# --- Errors (machine-readable) ---


class ErrorResponse(BaseModel):
    detail: str
    code: str = "error"
    correlation_id: str | None = None


# --- Pagination params (reusable) ---


class PaginationParams(BaseModel):
    limit: int = Field(default=20, ge=1, le=500, description="Page size")
    offset: int = Field(default=0, ge=0, description="Offset")
