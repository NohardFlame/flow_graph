"""LLMCallRepository: save, get, list_by_run."""

import uuid

from app.db.repositories import DocumentRepository, LLMCallRepository, RunRepository
from tests.db.conftest import document_factory, document_version_factory, llm_call_factory, run_factory


class TestLLMCallRepository:
    def test_save_and_get_and_list_by_run(
        self,
        document_repo: DocumentRepository,
        run_repo: RunRepository,
        llm_call_repo: LLMCallRepository,
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

        call_id = str(uuid.uuid4())
        llm_call = llm_call_factory(call_id, run_id, chunk_id=None)
        llm_call.provider = "openai"
        llm_call.model = "gpt-4"
        llm_call_repo.save(llm_call)

        loaded = llm_call_repo.get(call_id)
        assert loaded is not None
        assert loaded.provider == "openai"
        assert loaded.model == "gpt-4"

        by_run = llm_call_repo.list_by_run(run_id)
        assert len(by_run) == 1
        assert by_run[0].id == call_id
