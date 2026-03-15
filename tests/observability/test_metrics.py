"""Metrics: counters increment on run success/failure, prefilter, cache hit."""

import uuid
from datetime import datetime, timezone

import pytest

from app.core.constants import RunStatus
from app.core.errors import ParsingError
from app.core.metrics import InMemoryMetricsRecorder
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
from tests.fixtures.parse_fixtures import parsed_doc_simple_headings
from tests.observability.conftest import (
    _Clock,
    _IdGen,
    fake_storage,
    normalization_config,
    prefilter_service,
    session_factory,
)


def _parser_factory(doc_id: str, run_id: str):
    from tests.observability.conftest import FakeParser
    return FakeParser(doc_id, run_id)


class TestRunSuccessFailureCounters:
    """Run success and run failure increment metrics."""

    def test_run_success_increments_counters(self, orchestration_context):
        from app.adapters.llm.fake_llm_adapter import FakeLLMAdapter

        orchestrator, run_id, session, _ = orchestration_context
        metrics = InMemoryMetricsRecorder()
        orchestrator._metrics = metrics
        orchestrator.execute_run(run_id)
        session.commit()
        assert metrics.run_started >= 1
        assert metrics.run_succeeded >= 1
        assert metrics.run_failed == 0

    def test_run_failure_increments_failed_counter(
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
        parser_that_raises = lambda document_id, run_id: __class__._FakeParser(
            document_id, run_id, raise_on_parse=ParsingError("Unsupported")
        )
        metrics = InMemoryMetricsRecorder()
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
            metrics=metrics,
        )
        with pytest.raises(ParsingError):
            orchestrator.execute_run(run_id)
        assert metrics.run_started >= 1
        assert metrics.run_failed >= 1
        assert metrics.parse_failures >= 1

    class _FakeParser:
        def __init__(self, document_id: str, run_id: str, parsed_doc=None, raise_on_parse: BaseException | None = None):
            self._parsed_doc = parsed_doc or parsed_doc_simple_headings(document_id=document_id, run_id=run_id)
            self._raise_on_parse = raise_on_parse

        def parse(self, source: bytes | str, content_type: str | None = None):
            if self._raise_on_parse:
                raise self._raise_on_parse
            return self._parsed_doc


class TestPrefilterCounters:
    """Prefilter accept/gray/reject reflected in metrics."""

    def test_prefilter_counters_reflect_decisions(self, orchestration_context):
        orchestrator, run_id, session, _ = orchestration_context
        metrics = InMemoryMetricsRecorder()
        orchestrator._metrics = metrics
        orchestrator.execute_run(run_id)
        session.commit()
        total = metrics.prefilter_accept + metrics.prefilter_gray + metrics.prefilter_reject
        assert total >= 1


class TestCacheHitCounter:
    """Cache hit metric increments when LLM returns cached result."""

    def test_cache_hit_increments_when_llm_returns_cached(
        self,
        session_factory,
        fake_storage,
        normalization_config,
    ):
        from app.adapters.llm.fake_llm_adapter import FakeLLMAdapter
        from app.core.constants import PrefilterDecision
        from app.domain.extraction_models import ExtractionResult
        from app.domain.normalization_models import ExtractionDraft
        from app.services.prefilter.prefilter_models import PrefilterResult

        class FakePrefilterKeepAll:
            """Always return keep so extract_actions runs and LLM is called."""

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
        fake_storage.put_bytes(storage_key, b"content for parse", "text/plain")
        doc = Document(
            id=doc_id,
            original_filename="t.txt",
            content_type="text/plain",
            checksum_sha256="a" * 64,
            size_bytes=17,
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
        metrics = InMemoryMetricsRecorder()
        cached_result = ExtractionResult(
            drafts=[ExtractionDraft(verb="submit", primary_object="form")],
            raw_response="[]",
            provider="test",
            model="test",
            prompt_version="v1",
            schema_version="v1",
            cache_hit=True,
            retry_count=0,
            latency_ms=0,
            input_tokens=0,
            output_tokens=0,
            estimated_cost_usd=None,
            warnings=[],
        )
        class CachingFakeAdapter(FakeLLMAdapter):
            def extract_actions(self, chunk, prompt_cfg):
                return cached_result

            def extract_actions_batch(self, chunks, prompt_cfg):
                return cached_result
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
            llm_adapter=CachingFakeAdapter(extraction_responses=["[]"] * 100),
            normalization_config=normalization_config,
            id_generator=_IdGen(),
            clock=_Clock(),
            max_extract_retries=0,
            extraction_prompt_cfg={"prompt_version": "v1", "schema_version": "v1"},
            max_input_tokens=89600,
            extraction_context_chunks_up=0,
            metrics=metrics,
        )
        orchestrator.execute_run(run_id)
        session.commit()
        assert metrics.llm_calls >= 1
        assert metrics.llm_cache_hits >= 1
