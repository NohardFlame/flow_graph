"""Ingest service: upload raw file to storage then persist document and first version."""

import re
import uuid
from datetime import datetime, timezone

from app.core.checksum import sha256_hex
from app.core.protocols import IdGeneratorProtocol, ObjectStorageProtocol
from app.core.storage_keys import raw_source_key
from app.db.models import Document


def _sanitize_filename(filename: str, max_length: int = 512) -> str:
    """Take basename, remove control chars and path segments, truncate."""
    if not filename or not filename.strip():
        return "unnamed"
    # Strip path
    name = filename.replace("\\", "/").split("/")[-1].strip()
    # Remove control chars and nulls
    name = re.sub(r"[\x00-\x1f\x7f]", "", name)
    if not name:
        return "unnamed"
    return name[:max_length]


class IngestService:
    """Uploads file bytes to storage, then persists Document and first DocumentVersion.

    If storage upload fails, no DB write occurs. Caller must use same session for
    document_repo that they commit (or roll back) as needed.
    """

    def __init__(
        self,
        storage: ObjectStorageProtocol,
        document_repo: object,  # DocumentRepository with get(), save()
        *,
        id_generator: IdGeneratorProtocol | None = None,
    ) -> None:
        self._storage = storage
        self._document_repo = document_repo
        self._id_generator = id_generator

    def _generate_id(self) -> str:
        if self._id_generator is not None:
            return self._id_generator.generate()
        return str(uuid.uuid4())

    def ingest(
        self,
        body: bytes,
        original_filename: str,
        content_type: str,
    ) -> Document:
        """Upload body to storage, then save document and first version. Returns the created Document."""
        document_id = self._generate_id()
        version_id = self._generate_id()
        checksum_sha256 = sha256_hex(body)
        size_bytes = len(body)
        key = raw_source_key(document_id, version_id, content_type)
        metadata = {
            "checksum_sha256": checksum_sha256,
            "original_filename": _sanitize_filename(original_filename),
        }
        self._storage.put_bytes(key, body, content_type, metadata=metadata)
        now = datetime.now(timezone.utc)
        document = Document(
            id=document_id,
            original_filename=_sanitize_filename(original_filename),
            content_type=content_type,
            checksum_sha256=checksum_sha256,
            size_bytes=size_bytes,
            storage_key=key,
            created_at=now,
        )
        self._document_repo.save(  # type: ignore[union-attr]
            document,
            create_first_version=True,
            source_storage_key=key,
        )
        return document
