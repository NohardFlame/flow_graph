"""Protocol (interface) stubs for dependency injection.

Implementations are added in later phases. Services receive these via
constructor parameters; no service locator.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, BinaryIO, Protocol

from app.core.types import ActionId, ChunkId, DocumentId, ObjectMetadata, RunId
from app.domain.parse_models import ParsedDocument


class ClockProtocol(Protocol):
    """Provides current time (testable)."""

    def now(self) -> datetime: ...


class IdGeneratorProtocol(Protocol):
    """Generates unique IDs."""

    def generate(self) -> str: ...


class ObjectStorageProtocol(Protocol):
    """S3-compatible object storage contract."""

    def put_bytes(
        self,
        key: str,
        body: bytes,
        content_type: str,
        metadata: dict[str, str] | None = None,
    ) -> None: ...
    def put_file(
        self,
        key: str,
        file_path: str | Path,
        content_type: str,
        metadata: dict[str, str] | None = None,
    ) -> None: ...
    def get_stream(self, key: str) -> BinaryIO: ...
    def download_to_tempfile(self, key: str) -> Path: ...
    def head(self, key: str) -> ObjectMetadata: ...
    def delete(self, key: str) -> None: ...


class DocumentParserProtocol(Protocol):
    """Document conversion to structured parse result. Implementors return ParsedDocument."""

    def parse(self, source: bytes | str, content_type: str | None = None) -> ParsedDocument: ...


class LLMClientProtocol(Protocol):
    """LLM gateway for extraction."""

    def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str: ...


class VectorIndexProtocol(Protocol):
    """Optional vector search (e.g. Qdrant)."""

    def index(self, id: str, vector: list[float], payload: dict[str, Any]) -> None: ...
    def search(self, vector: list[float], limit: int) -> list[dict[str, Any]]: ...


class RunRepositoryProtocol(Protocol):
    """Persistence for processing runs."""

    def get(self, run_id: RunId) -> Any | None: ...
    def save(self, run: Any) -> Any: ...
    def update_status(self, run_id: RunId, status: str, **kwargs: Any) -> None: ...


class DocumentRepositoryProtocol(Protocol):
    """Persistence for documents."""

    def get(self, document_id: DocumentId) -> Any | None: ...
    def save(self, document: Any) -> Any: ...


class ActionRepositoryProtocol(Protocol):
    """Persistence for extracted actions."""

    def get(self, action_id: ActionId) -> Any | None: ...
    def save(self, action: Any) -> Any: ...
    def list_by_run(self, run_id: RunId, limit: int | None = None, offset: int = 0) -> list[Any]: ...


class ChunkRepositoryProtocol(Protocol):
    """Persistence for extraction chunks. Idempotent by (run_id, chunk_hash)."""

    def upsert_chunk(
        self,
        run_id: RunId,
        chunk_hash: str,
        text: str,
        *,
        section_path: dict[str, Any] | None = None,
        page_refs: dict[str, Any] | None = None,
        estimated_tokens: int | None = None,
        prefilter_score: float | None = None,
        prefilter_decision: str | None = None,
        prefilter_features: dict[str, Any] | None = None,
    ) -> Any: ...
    def list_by_run(
        self, run_id: RunId, limit: int | None = None, offset: int = 0
    ) -> list[Any]: ...
    def list_by_run_and_decision(self, run_id: RunId, decision: str) -> list[Any]: ...


class LLMCallRepositoryProtocol(Protocol):
    """Persistence for LLM call audit records."""

    def save(self, llm_call: Any) -> Any: ...
    def get(self, llm_call_id: str) -> Any | None: ...
    def list_by_run(self, run_id: RunId) -> list[Any]: ...


class RunEventRepositoryProtocol(Protocol):
    """Persistence for run step events."""

    def append(self, run_id: RunId, step: str, event_type: str, payload: dict[str, Any] | None = None) -> Any: ...
    def list_by_run(self, run_id: RunId) -> list[Any]: ...


class JobQueueProtocol(Protocol):
    """Enqueue processing jobs. Phase 8 adds real worker queue; this is for API to enqueue after run creation."""

    def enqueue(self, payload: dict[str, Any]) -> None: ...
