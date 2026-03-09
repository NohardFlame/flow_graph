"""Document and document_version persistence."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Document, DocumentVersion


class DocumentRepository:
    """Persistence for documents. Session injected; one transaction per operation."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, document_id: str) -> Document | None:
        return self._session.get(Document, document_id)

    def get_latest_version(self, document_id: str) -> DocumentVersion | None:
        """Return the latest document version by version_number, or None if no versions."""
        result = self._session.execute(
            select(DocumentVersion)
            .where(DocumentVersion.document_id == document_id)
            .order_by(DocumentVersion.version_number.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    def save(
        self,
        document: Document,
        *,
        create_first_version: bool = False,
        source_storage_key: str | None = None,
    ) -> Document:
        self._session.add(document)
        if create_first_version and source_storage_key is not None:
            version = DocumentVersion(
                id=str(uuid.uuid4()),
                document_id=document.id,
                version_number=1,
                source_storage_key=source_storage_key,
                created_at=datetime.now(timezone.utc),
            )
            self._session.add(version)
        self._session.flush()
        return document
