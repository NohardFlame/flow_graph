"""Protocol (interface) stubs for dependency injection.

Implementations are added in later phases. Services receive these via
constructor parameters; no service locator.
"""

from datetime import datetime
from typing import Any, Protocol

from app.core.types import ActionId, DocumentId, RunId


class ClockProtocol(Protocol):
    """Provides current time (testable)."""

    def now(self) -> datetime: ...


class IdGeneratorProtocol(Protocol):
    """Generates unique IDs."""

    def generate(self) -> str: ...


class ObjectStorageProtocol(Protocol):
    """S3-compatible object storage contract."""

    def upload(self, key: str, body: bytes, content_type: str, metadata: dict[str, str] | None = None) -> None: ...
    def download(self, key: str) -> bytes: ...
    def delete(self, key: str) -> None: ...
    def exists(self, key: str) -> bool: ...


class DocumentParserProtocol(Protocol):
    """Document conversion to structured parse result."""

    def parse(self, source: bytes | str, content_type: str | None = None) -> Any: ...


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
    def list_by_run(self, run_id: RunId) -> list[Any]: ...
