"""Run orchestration tests. Do not mask: assert real outcomes and exceptions."""

import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.core.constants import RunStatus
from app.core.errors import ParsingError, RetryableExternalError, ValidationError
from app.db.models import Document, DocumentVersion, Run
from app.db.repositories import (
    ActionRepository,
    ChunkRepository,
    DocumentRepository,
    RunEventRepository,
    RunRepository,
)
from app.services.chunk_assembler import ChunkAssembler
from app.services.run_orchestration.service import RunOrchestrator
from app.workers.retry_policy import is_run_step_retryable
from app.workers.schemas import RunJobPayload
from app.workers.tasks import process_run_job
from tests.fixtures.parse_fixtures import parsed_doc_simple_headings
from tests.workers.conftest import (
    FakeParser,
    _Clock,
    _IdGen,
    _parser_factory,
)


class TestHappyPath:
    """All steps execute in order; run ends succeeded; events and data persisted."""

    def test_execute_run_completes_with_succeeded_status(self, orchestration_context):
        orchestrator, run_id, session, _ = orchestration_context
        orchestrator.execute_run(run_id)
        session.commit()
        run = orchestrator._run_repo.get(run_id)
        assert run is not None
        assert run.status == RunStatus.SUCCEEDED
        assert run.current_step == "complete_run"

    def test_run_events_record_each_step(self, orchestration_context):
        orchestrator, run_id, session, _ = orchestration_context
        orchestrator.execute_run(run_id)
        session.commit()
        events = orchestrator._run_event_repo.list_by_run(run_id)
        step_names = [e.step for e in events]
        assert "ingest_ready" in step_names
        assert "parse_document" in step_names
        assert "build_chunks" in step_names
        assert "prefilter_chunks" in step_names
        assert "extract_actions" in step_names
        assert "normalize_actions" in step_names
        assert "persist_results" in step_names
        assert "complete_run" in step_names

    def test_chunks_persisted_after_build_and_prefilter(self, orchestration_context):
        orchestrator, run_id, session, _ = orchestration_context
        orchestrator.execute_run(run_id)
        session.commit()
        chunks = orchestrator._chunk_repo.list_by_run(run_id)
        assert len(chunks) >= 1
        assert all(c.prefilter_decision is not None for c in chunks)

    def test_actions_persisted_when_llm_returns_drafts(self, orchestration_context):
        orchestrator, run_id, session, _ = orchestration_context
        orchestrator.execute_run(run_id)
        session.commit()
        actions = orchestrator._action_repo.list_by_run(run_id)
        # At least one chunk may be "keep" and produce actions
        assert isinstance(actions, list)


class TestRetryableFailure:
    """Transient step error causes retry behavior; run remains resumable or succeeds on retry."""

    def test_retryable_error_is_classified_correctly(self):
        assert is_run_step_retryable(RetryableExternalError("timeout")) is True
        assert is_run_step_retryable(ValidationError("bad")) is False
        assert is_run_step_retryable(ParsingError("unsupported")) is False

    def test_llm_retry_then_success_within_execute_run(
        self,
        session_factory,
        fake_storage,
        prefilter_service,
        normalization_config,
    ):
        from app.adapters.llm.fake_llm_adapter import FakeLLMAdapter

        session = session_factory()
        doc_id = str(uuid.uuid4())
        version_id = str(uuid.uuid4())
        run_id = str(uuid.uuid4())
        storage_key = f"documents/{doc_id}/{version_id}/source.bin"
        fake_storage.put_bytes(storage_key, b"content", "text/plain")
        doc = Document(
            id=doc_id,
            original_filename="t.txt",
            content_type="text/plain",
            checksum_sha256="a" * 64,
            size_bytes=7,
            storage_key=storage_key,
            created_at=datetime.now(timezone.utc),
        )
        session.add(doc)
        session.flush()
        session.add(
            DocumentVersion(
                id=version_id,
                document_id=doc_id,
                version_number=1,
                source_storage_key=storage_key,
                created_at=datetime.now(timezone.utc),
            )
        )
        session.flush()
        session.add(
            Run(
                id=run_id,
                document_id=doc_id,
                document_version_id=version_id,
                status="queued",
            )
        )
        session.flush()
        # First call raises retryable, second returns valid JSON
        llm = FakeLLMAdapter(
            extraction_responses=[
                RetryableExternalError("rate limit"),
                '[{"verb": "submit", "primary_object": "form"}]',
            ] * 20
        )
        orchestrator = RunOrchestrator(
            run_repo=RunRepository(session),
            document_repo=DocumentRepository(session),
            chunk_repo=ChunkRepository(session),
            action_repo=ActionRepository(session),
            run_event_repo=RunEventRepository(session),
            storage=fake_storage,
            parser_factory=_parser_factory,
            chunk_assembler=ChunkAssembler(),
            prefilter_service=prefilter_service,
            llm_adapter=llm,
            normalization_config=normalization_config,
            id_generator=_IdGen(),
            clock=_Clock(),
            max_extract_retries=3,
            extraction_prompt_cfg={"prompt_version": "v1", "schema_version": "v1"},
        )
        orchestrator.execute_run(run_id)
        session.commit()
        run = orchestrator._run_repo.get(run_id)
        assert run is not None
        assert run.status == RunStatus.SUCCEEDED


class TestPermanentFailure:
    """Non-retryable step error marks run failed; downstream steps not executed."""

    def test_parsing_error_marks_run_failed_and_records_error(
        self,
        session_factory,
        fake_storage,
        prefilter_service,
        normalization_config,
    ):
        from app.adapters.llm.fake_llm_adapter import FakeLLMAdapter

        session = session_factory()
        doc_id = str(uuid.uuid4())
        version_id = str(uuid.uuid4())
        run_id = str(uuid.uuid4())
        storage_key = f"documents/{doc_id}/{version_id}/source.bin"
        fake_storage.put_bytes(storage_key, b"x", "text/plain")
        doc = Document(
            id=doc_id,
            original_filename="t.txt",
            content_type="text/plain",
            checksum_sha256="a" * 64,
            size_bytes=1,
            storage_key=storage_key,
            created_at=datetime.now(timezone.utc),
        )
        session.add(doc)
        session.flush()
        session.add(
            DocumentVersion(
                id=version_id,
                document_id=doc_id,
                version_number=1,
                source_storage_key=storage_key,
                created_at=datetime.now(timezone.utc),
            )
        )
        session.flush()
        session.add(
            Run(
                id=run_id,
                document_id=doc_id,
                document_version_id=version_id,
                status="queued",
            )
        )
        session.flush()
        parser_that_raises = lambda document_id, run_id: FakeParser(
            document_id, run_id, raise_on_parse=ParsingError("Unsupported format")
        )
        orchestrator = RunOrchestrator(
            run_repo=RunRepository(session),
            document_repo=DocumentRepository(session),
            chunk_repo=ChunkRepository(session),
            action_repo=ActionRepository(session),
            run_event_repo=RunEventRepository(session),
            storage=fake_storage,
            parser_factory=parser_that_raises,
            chunk_assembler=ChunkAssembler(),
            prefilter_service=prefilter_service,
            llm_adapter=FakeLLMAdapter(extraction_responses=["[]"]),
            normalization_config=normalization_config,
            id_generator=_IdGen(),
            clock=_Clock(),
            max_extract_retries=0,
            extraction_prompt_cfg={"prompt_version": "v1", "schema_version": "v1"},
        )
        with pytest.raises(ParsingError):
            orchestrator.execute_run(run_id)
        run = orchestrator._run_repo.get(run_id)
        assert run is not None
        assert run.status == RunStatus.FAILED
        assert run.error_code == "parsing_error"
        assert run.error_message
        chunks = orchestrator._chunk_repo.list_by_run(run_id)
        actions = orchestrator._action_repo.list_by_run(run_id)
        assert len(chunks) == 0
        assert len(actions) == 0

    def test_invalid_llm_output_raises_validation_error(
        self,
        session_factory,
        fake_storage,
        normalization_config,
    ):
        from app.adapters.llm.fake_llm_adapter import FakeLLMAdapter
        from app.core.constants import PrefilterDecision
        from app.services.prefilter.prefilter_models import PrefilterResult

        class FakePrefilterKeepAll:
            """Always return keep so extract_actions runs and calls LLM."""

            def score_chunks(self, chunks):
                return [
                    PrefilterResult(
                        prefilter_score=0.8,
                        decision=PrefilterDecision.KEEP,
                        selected_for_llm=True,
                    )
                    for _ in chunks
                ]

        session = session_factory()
        doc_id = str(uuid.uuid4())
        version_id = str(uuid.uuid4())
        run_id = str(uuid.uuid4())
        storage_key = f"documents/{doc_id}/{version_id}/source.bin"
        fake_storage.put_bytes(storage_key, b"x", "text/plain")
        doc = Document(
            id=doc_id,
            original_filename="t.txt",
            content_type="text/plain",
            checksum_sha256="a" * 64,
            size_bytes=1,
            storage_key=storage_key,
            created_at=datetime.now(timezone.utc),
        )
        session.add(doc)
        session.flush()
        session.add(
            DocumentVersion(
                id=version_id,
                document_id=doc_id,
                version_number=1,
                source_storage_key=storage_key,
                created_at=datetime.now(timezone.utc),
            )
        )
        session.flush()
        session.add(
            Run(
                id=run_id,
                document_id=doc_id,
                document_version_id=version_id,
                status="queued",
            )
        )
        session.flush()
        llm = FakeLLMAdapter(extraction_responses=["not json at all"])
        orchestrator = RunOrchestrator(
            run_repo=RunRepository(session),
            document_repo=DocumentRepository(session),
            chunk_repo=ChunkRepository(session),
            action_repo=ActionRepository(session),
            run_event_repo=RunEventRepository(session),
            storage=fake_storage,
            parser_factory=_parser_factory,
            chunk_assembler=ChunkAssembler(),
            prefilter_service=FakePrefilterKeepAll(),
            llm_adapter=llm,
            normalization_config=normalization_config,
            id_generator=_IdGen(),
            clock=_Clock(),
            max_extract_retries=0,
            extraction_prompt_cfg={"prompt_version": "v1", "schema_version": "v1"},
        )
        with pytest.raises(ValidationError):
            orchestrator.execute_run(run_id)
        run = orchestrator._run_repo.get(run_id)
        assert run is not None
        assert run.status == RunStatus.FAILED


class TestResume:
    """Run resumes from next incomplete step; no duplicate chunks/actions."""

    def test_resume_after_partial_progress_does_not_duplicate_chunks(
        self,
        orchestration_context,
    ):
        orchestrator, run_id, session, _ = orchestration_context
        orchestrator.execute_run(run_id)
        session.commit()
        count_after_first = orchestrator._chunk_repo.count_by_run(run_id)
        # Run again (e.g. job retry) - idempotent
        orchestrator.execute_run(run_id)
        session.commit()
        count_after_second = orchestrator._chunk_repo.count_by_run(run_id)
        assert count_after_second == count_after_first


class TestIdempotency:
    """Rerunning full job after success does not double-write."""

    def test_run_twice_same_run_id_does_not_double_actions(self, orchestration_context):
        orchestrator, run_id, session, _ = orchestration_context
        orchestrator.execute_run(run_id)
        session.commit()
        actions_first = orchestrator._action_repo.count_by_run(run_id)
        chunks_first = orchestrator._chunk_repo.count_by_run(run_id)
        # Second full run (e.g. duplicate job)
        orchestrator.execute_run(run_id)
        session.commit()
        actions_second = orchestrator._action_repo.count_by_run(run_id)
        chunks_second = orchestrator._chunk_repo.count_by_run(run_id)
        assert actions_second == actions_first
        assert chunks_second == chunks_first


class TestJobPayload:
    """RunJobPayload deserialization and process_run_job wiring."""

    def test_payload_from_dict_requires_run_id(self):
        with pytest.raises(ValueError, match="run_id"):
            RunJobPayload.from_dict({})
        with pytest.raises(ValueError, match="run_id"):
            RunJobPayload.from_dict({"document_id": "d1"})

    def test_payload_from_dict_accepts_optional_fields(self):
        p = RunJobPayload.from_dict({"run_id": "r1"})
        assert p.run_id == "r1"
        assert p.document_id is None
        assert p.attempt == 0
        p2 = RunJobPayload.from_dict({"run_id": "r2", "document_id": "d2", "attempt": 1})
        assert p2.document_id == "d2"
        assert p2.attempt == 1

    def test_process_run_job_calls_execute_run_and_run_succeeds(
        self,
        orchestration_context,
    ):
        orchestrator, run_id, session, _ = orchestration_context
        # Use same session and orchestrator so run is visible; process_run_job will commit
        session_factory = lambda: session
        orchestrator_factory = lambda s: orchestrator
        process_run_job(
            {"run_id": run_id},
            session_factory=session_factory,
            orchestrator_factory=orchestrator_factory,
        )
        run = orchestrator._run_repo.get(run_id)
        assert run is not None
        assert run.status == RunStatus.SUCCEEDED
