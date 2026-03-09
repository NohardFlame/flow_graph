"""RunEventRepository: append, list_by_run."""

import uuid

from app.db.repositories import DocumentRepository, RunEventRepository, RunRepository
from tests.db.conftest import document_factory, document_version_factory, run_factory


class TestRunEventRepository:
    def test_append_and_list_by_run(
        self,
        document_repo: DocumentRepository,
        run_repo: RunRepository,
        run_event_repo: RunEventRepository,
    ):
        doc_id = str(uuid.uuid4())
        version_id = str(uuid.uuid4())
        run_id = str(uuid.uuid4())
        doc = document_factory(doc_id)
        document_repo.save(doc, create_first_version=True, source_storage_key="s3://k")
        version = document_version_factory(version_id, doc_id, source_storage_key="s3://k")
        document_repo._session.add(version)
        document_repo._session.flush()
        run = run_factory(run_id, doc_id, version_id)
        run_repo.save(run)

        run_event_repo.append(run_id, "parse", "step_started", {"elapsed_ms": 0})
        run_event_repo.append(run_id, "parse", "step_finished", {"elapsed_ms": 100})

        events = run_event_repo.list_by_run(run_id)
        assert len(events) == 2
        assert events[0].step == "parse"
        assert events[0].event_type == "step_started"
        assert events[1].event_type == "step_finished"
