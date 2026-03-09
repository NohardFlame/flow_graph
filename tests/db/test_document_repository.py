"""DocumentRepository: basic persistence and get/save."""

import uuid

from app.db.repositories import DocumentRepository
from tests.db.conftest import document_factory


class TestDocumentRepositoryBasicPersistence:
    def test_save_and_get(self, document_repo: DocumentRepository):
        doc_id = str(uuid.uuid4())
        doc = document_factory(doc_id)
        document_repo.save(doc)
        loaded = document_repo.get(doc_id)
        assert loaded is not None
        assert loaded.id == doc_id
        assert loaded.original_filename == doc.original_filename
        assert loaded.storage_key == doc.storage_key

    def test_get_returns_none_when_missing(self, document_repo: DocumentRepository):
        assert document_repo.get(str(uuid.uuid4())) is None

    def test_save_with_first_version(self, document_repo: DocumentRepository):
        doc_id = str(uuid.uuid4())
        doc = document_factory(doc_id)
        document_repo.save(doc, create_first_version=True, source_storage_key="s3://bucket/v1")
        loaded = document_repo.get(doc_id)
        assert loaded is not None
        assert len(loaded.versions) == 1
        assert loaded.versions[0].version_number == 1
        assert loaded.versions[0].source_storage_key == "s3://bucket/v1"
