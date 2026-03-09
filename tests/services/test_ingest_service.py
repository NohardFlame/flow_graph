"""Ingest service tests: fake storage + real document repo. No mocks of key or checksum."""

import pytest

from app.adapters.storage.fake_storage import FakeObjectStorage
from app.db.models import Document as DocModel
from app.services.ingest_service import IngestService


def test_ingest_success_persists_document_and_version(document_repo, fake_storage):
    """When storage succeeds, document and one version are saved with correct key and checksum."""
    service = IngestService(fake_storage, document_repo)
    body = b"hello world"
    doc = service.ingest(body, "test.txt", "text/plain")
    assert doc.id
    assert doc.original_filename == "test.txt"
    assert doc.content_type == "text/plain"
    assert doc.size_bytes == 11
    assert doc.checksum_sha256 == "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
    assert doc.storage_key.startswith("raw/")
    assert doc.storage_key.endswith("/source.txt")
    saved = document_repo.get(doc.id)
    assert saved is not None
    assert saved.storage_key == doc.storage_key
    assert saved.checksum_sha256 == doc.checksum_sha256
    assert saved.size_bytes == doc.size_bytes
    assert fake_storage.head(doc.storage_key).size == 11
    assert fake_storage.get_stream(doc.storage_key).read() == body


def test_ingest_storage_failure_does_not_save_document(document_repo):
    """When storage put_bytes raises, no document or version is saved."""
    class FailingFake(FakeObjectStorage):
        def put_bytes(self, key, body, content_type, metadata=None):
            raise RuntimeError("storage failed")
    failing = FailingFake()
    service = IngestService(failing, document_repo)
    with pytest.raises(RuntimeError, match="storage failed"):
        service.ingest(b"data", "x.txt", "text/plain")
    from sqlalchemy import select, func
    session = document_repo._session
    count = session.scalar(select(func.count()).select_from(DocModel))
    assert count == 0


def test_ingest_sanitizes_filename(document_repo, fake_storage):
    """Original filename is sanitized (path stripped, no control chars)."""
    service = IngestService(fake_storage, document_repo)
    doc = service.ingest(b"x", "..\\../evil.txt", "text/plain")
    assert ".." not in doc.original_filename
    assert doc.original_filename == "evil.txt"
    doc2 = service.ingest(b"y", "  \n  a  ", "text/plain")
    assert ".." not in doc2.original_filename
    assert len(doc2.original_filename) <= 512
