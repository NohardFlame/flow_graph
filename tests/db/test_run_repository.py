"""RunRepository: create run, update status."""

import uuid

from app.core.constants import RunStatus
from app.db.repositories import ActionRepository, ChunkRepository, DocumentRepository, RunRepository
from tests.db.conftest import action_factory, document_factory, document_version_factory, run_factory


class TestRunRepositoryBasicPersistence:
    def test_save_and_get(self, document_repo: DocumentRepository, run_repo: RunRepository):
        doc_id = str(uuid.uuid4())
        version_id = str(uuid.uuid4())
        doc = document_factory(doc_id)
        document_repo.save(doc, create_first_version=True, source_storage_key="s3://key")
        version = document_version_factory(version_id, doc_id, source_storage_key="s3://key")
        document_repo._session.add(version)
        document_repo._session.flush()

        run_id = str(uuid.uuid4())
        run = run_factory(run_id, doc_id, version_id, status=RunStatus.PENDING)
        run_repo.save(run)
        loaded = run_repo.get(run_id)
        assert loaded is not None
        assert loaded.status == RunStatus.PENDING

    def test_update_status(self, document_repo: DocumentRepository, run_repo: RunRepository):
        doc_id = str(uuid.uuid4())
        version_id = str(uuid.uuid4())
        doc = document_factory(doc_id)
        document_repo.save(doc, create_first_version=True, source_storage_key="s3://key")
        version = document_version_factory(version_id, doc_id, source_storage_key="s3://key")
        document_repo._session.add(version)
        document_repo._session.flush()

        run_id = str(uuid.uuid4())
        run = run_factory(run_id, doc_id, version_id, status=RunStatus.PENDING)
        run_repo.save(run)

        run_repo.update_status(run_id, RunStatus.RUNNING, current_step="parse")
        loaded = run_repo.get(run_id)
        assert loaded.status == RunStatus.RUNNING
        assert loaded.current_step == "parse"

    def test_fetch_run_with_chunk_and_action_counts(
        self,
        document_repo: DocumentRepository,
        run_repo: RunRepository,
        chunk_repo: ChunkRepository,
        action_repo: ActionRepository,
    ):
        doc_id = str(uuid.uuid4())
        version_id = str(uuid.uuid4())
        doc = document_factory(doc_id)
        document_repo.save(doc, create_first_version=True, source_storage_key="s3://k")
        version = document_version_factory(version_id, doc_id, source_storage_key="s3://k")
        document_repo._session.add(version)
        document_repo._session.flush()

        run_id = str(uuid.uuid4())
        run = run_factory(run_id, doc_id, version_id)
        run_repo.save(run)

        chunk_repo.upsert_chunk(run_id, "h1", "text1")
        chunk_repo.upsert_chunk(run_id, "h2", "text2")
        action_repo.save(action_factory(str(uuid.uuid4()), run_id, "A", "a"))
        action_repo.save(action_factory(str(uuid.uuid4()), run_id, "B", "b"))

        loaded = run_repo.get(run_id)
        assert loaded is not None
        assert len(loaded.chunks) == 2
        assert len(loaded.actions) == 2
