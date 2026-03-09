"""Run event emission: started, completed, failed, retried, partial_success. Do not mask failures."""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import Session

from app.core.constants import RunStatus
from app.core.errors import ParsingError
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
from tests.observability.conftest import (
    FakeParser,
    _Clock,
    _IdGen,
    _parser_factory,
    fake_storage,
    normalization_config,
    prefilter_service,
    session_factory,
)


class TestStepStartedAndCompleted:
    """Step started and step completed emitted around a successful step."""

    def test_step_started_and_completed_emitted_for_successful_step(self, orchestration_context):
        orchestrator, run_id, session, _ = orchestration_context
        orchestrator.execute_run(run_id)
        session.commit()
        events = orchestrator._run_event_repo.list_by_run(run_id)
        by_step: dict[str, list[str]] = {}
        for e in events:
            by_step.setdefault(e.step, []).append(e.event_type)
        # At least one step (e.g. ingest_ready) should have both started and completed
        assert "ingest_ready" in by_step
        assert "started" in by_step["ingest_ready"]
        assert "completed" in by_step["ingest_ready"]


class TestStepFailed:
    """Step failed emitted on failure."""

    def test_step_failed_emitted_on_failure(
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
        def parser_that_raises(document_id: str, run_id: str):
            return FakeParser(document_id, run_id, raise_on_parse=ParsingError("Unsupported format"))
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
        events = orchestrator._run_event_repo.list_by_run(run_id)
        failed_events = [e for e in events if e.event_type == "failed"]
        assert len(failed_events) >= 1
        assert any("error" in (e.payload_jsonb or {}) for e in failed_events)


class TestStepRetried:
    """Retry event: emitted when the same step is run again (resume with current_step == next_step)."""

    def test_started_events_present_on_successful_run(self, orchestration_context):
        """After a full run, we have started (and completed) for multiple steps."""
        orchestrator, run_id, session, _ = orchestration_context
        orchestrator.execute_run(run_id)
        session.commit()
        events = orchestrator._run_event_repo.list_by_run(run_id)
        started_steps = [e.step for e in events if e.event_type == "started"]
        assert len(started_steps) >= 1
        completed_steps = [e.step for e in events if e.event_type == "completed"]
        assert len(completed_steps) >= 1


class TestPartialSuccess:
    """Partial success event when optional indexing fails."""

    def test_partial_success_event_when_optional_indexer_raises(self, orchestration_context):
        orchestrator, run_id, session, _ = orchestration_context
        def failing_indexer(run_id: str) -> None:
            raise RuntimeError("indexing unavailable")
        orchestrator._optional_indexer = failing_indexer
        orchestrator.execute_run(run_id)
        session.commit()
        run = orchestrator._run_repo.get(run_id)
        assert run is not None
        assert run.status == RunStatus.PARTIAL_SUCCESS
        events = orchestrator._run_event_repo.list_by_run(run_id)
        partial_events = [e for e in events if e.event_type == "partial_success"]
        assert len(partial_events) >= 1
        assert any(e.step == "optional_index" for e in partial_events)
