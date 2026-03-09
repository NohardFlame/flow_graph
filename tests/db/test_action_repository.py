"""ActionRepository: save with evidence, list by run, idempotency by (run_id, action_canonical)."""

import uuid

from app.db.repositories import ActionRepository, DocumentRepository, RunRepository
from tests.db.conftest import (
    action_evidence_factory,
    action_factory,
    document_factory,
    document_version_factory,
    run_factory,
)


class TestActionRepositoryBasicPersistence:
    def test_save_and_get_with_evidence(
        self,
        document_repo: DocumentRepository,
        run_repo: RunRepository,
        action_repo: ActionRepository,
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

        action_id = str(uuid.uuid4())
        action = action_factory(
            action_id,
            run_id,
            "Submit form",
            "submit_form",
            raw_jsonb={"actor": "user"},
        )
        evidence = [
            action_evidence_factory(str(uuid.uuid4()), action_id, "snippet one"),
        ]
        action_repo.save(action, evidence=evidence)
        loaded = action_repo.get(action_id)
        assert loaded is not None
        assert loaded.action_canonical == "submit_form"
        assert len(loaded.evidence) == 1
        assert loaded.evidence[0].snippet == "snippet one"

    def test_list_by_run_pagination(
        self,
        document_repo: DocumentRepository,
        run_repo: RunRepository,
        action_repo: ActionRepository,
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

        for i in range(5):
            action = action_factory(str(uuid.uuid4()), run_id, f"Action {i}", f"action_{i}")
            action_repo.save(action)

        all_ = action_repo.list_by_run(run_id)
        assert len(all_) == 5
        page1 = action_repo.list_by_run(run_id, limit=2, offset=0)
        assert len(page1) == 2
        page2 = action_repo.list_by_run(run_id, limit=2, offset=2)
        assert len(page2) == 2

    def test_save_idempotent_by_run_id_action_canonical(
        self,
        document_repo: DocumentRepository,
        run_repo: RunRepository,
        action_repo: ActionRepository,
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

        action1 = action_factory(str(uuid.uuid4()), run_id, "Label A", "canonical_a", raw_jsonb={"v": 1})
        action_repo.save(action1)
        action2 = action_factory(str(uuid.uuid4()), run_id, "Label A updated", "canonical_a", raw_jsonb={"v": 2})
        action_repo.save(action2)

        by_run = action_repo.list_by_run(run_id)
        assert len(by_run) == 1
        assert by_run[0].action_label == "Label A updated"
        assert by_run[0].raw_jsonb == {"v": 2}
