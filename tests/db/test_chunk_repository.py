"""ChunkRepository: upsert idempotency, list by run and decision."""

import uuid

from app.core.constants import PrefilterDecision
from app.db.repositories import ChunkRepository, DocumentRepository, RunRepository
from tests.db.conftest import document_factory, document_version_factory, run_factory


class TestChunkRepositoryIdempotency:
    def test_upsert_twice_same_run_id_chunk_hash_does_not_duplicate(
        self,
        document_repo: DocumentRepository,
        run_repo: RunRepository,
        chunk_repo: ChunkRepository,
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

        chunk_repo.upsert_chunk(
            run_id,
            "hash1",
            "first text",
            prefilter_decision=PrefilterDecision.KEEP,
        )
        chunk_repo.upsert_chunk(
            run_id,
            "hash1",
            "updated text",
            prefilter_decision=PrefilterDecision.GRAY,
        )
        rows = chunk_repo.list_by_run(run_id)
        assert len(rows) == 1
        assert rows[0].text == "updated text"
        assert rows[0].prefilter_decision == PrefilterDecision.GRAY

    def test_list_by_run_and_decision(
        self,
        document_repo: DocumentRepository,
        run_repo: RunRepository,
        chunk_repo: ChunkRepository,
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

        chunk_repo.upsert_chunk(run_id, "h1", "t1", prefilter_decision=PrefilterDecision.KEEP)
        chunk_repo.upsert_chunk(run_id, "h2", "t2", prefilter_decision=PrefilterDecision.REJECT)
        chunk_repo.upsert_chunk(run_id, "h3", "t3", prefilter_decision=PrefilterDecision.KEEP)

        keep = chunk_repo.list_by_run_and_decision(run_id, PrefilterDecision.KEEP)
        assert len(keep) == 2
        reject = chunk_repo.list_by_run_and_decision(run_id, PrefilterDecision.REJECT)
        assert len(reject) == 1
