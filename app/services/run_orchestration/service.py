"""Run pipeline step runner: execute_run orchestrates parse -> chunk -> prefilter -> extract -> normalize -> persist."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any, Optional

from app.adapters.llm.prompt_builder import BATCH_CHUNK_SEPARATOR
from app.adapters.llm.retry_repair import ExtractActionsProtocol, extract_batch_with_retry
from app.core.constants import (
    EXTRACTION_PROMPT_VERSION,
    EXTRACTION_SCHEMA_VERSION,
    PrefilterDecision,
    RUN_PIPELINE_STEPS,
    RunStatus,
)
from app.core.errors import (
    NotFoundError,
    ParsingError,
    RetryableExternalError,
    StorageNotFoundError,
    ValidationError,
)
from app.core.metrics import MetricsRecorder
from app.core.normalization_config import NormalizationConfig
from app.core.protocols import (
    ClockProtocol,
    IdGeneratorProtocol,
    ObjectStorageProtocol,
)
from app.db.models import Chunk, Run
from app.db.repositories.action_repository import ActionRepository
from app.db.repositories.chunk_repository import ChunkRepository
from app.db.repositories.document_repository import DocumentRepository
from app.db.repositories.run_event_repository import RunEventRepository
from app.db.repositories.run_repository import RunRepository
from app.domain.extraction_models import ExtractionResult
from app.domain.normalization_models import NormalizedActionRecord
from app.domain.parse_models import ExtractionChunk, ParsedDocument, merge_parsed_documents
from app.core.token_estimate import estimated_tokens
from app.services.action_persistence import build_action_entities
from app.services.chunk_assembler import ChunkAssembler
from app.services.extraction_batching import (
    batch_chunks_for_context,
    build_batch_chunk_hash,
    expand_with_context_chunks,
)
from app.services.normalization_service import normalize_batch
from app.services.parse_artifact_service import save_parse_artifacts
from app.services.prefilter.prefilter_models import PrefilterResult
from app.services.prefilter.service import PrefilterService
from app.config.logging import get_logger, log_structured
from app.workers.retry_policy import error_code_for_run, is_run_step_retryable

_LOG = get_logger(__name__)


def _chunk_to_extraction_chunk(c: Chunk) -> ExtractionChunk:
    """Build ExtractionChunk from persisted Chunk for prefilter/LLM."""
    section_path = c.section_path_jsonb if isinstance(c.section_path_jsonb, list) else (c.section_path_jsonb.get("path", []) if isinstance(c.section_path_jsonb, dict) else [])
    page_refs = c.page_refs_jsonb if isinstance(c.page_refs_jsonb, list) else (c.page_refs_jsonb.get("refs", []) if isinstance(c.page_refs_jsonb, dict) else [])
    return ExtractionChunk(
        chunk_id=c.chunk_hash,
        section_path=section_path,
        chunk_text=c.text or "",
        source_spans={},
        page_refs=page_refs,
        estimated_tokens=c.estimated_tokens or 0,
        structural_features=dict(c.prefilter_features_jsonb) if c.prefilter_features_jsonb else {},
    )


def _section_path_for_repo(path: list[str]) -> dict[str, Any]:
    """ChunkRepository expects section_path as dict for JSONB."""
    return {"path": path}


def _page_refs_for_repo(refs: list[dict[str, Any]]) -> dict[str, Any]:
    """ChunkRepository expects page_refs as dict for JSONB."""
    return {"refs": refs}


class RunOrchestrator:
    """Executes the document pipeline step by step with persistence and events."""

    def __init__(
        self,
        *,
        run_repo: RunRepository,
        document_repo: DocumentRepository,
        chunk_repo: ChunkRepository,
        action_repo: ActionRepository,
        run_event_repo: RunEventRepository,
        storage: ObjectStorageProtocol,
        parser_factory: Callable[[str, str], Any],  # (document_id, run_id) -> DocumentParserProtocol
        chunk_assembler: ChunkAssembler,
        prefilter_service: PrefilterService,
        llm_adapter: ExtractActionsProtocol,
        normalization_config: NormalizationConfig,
        id_generator: IdGeneratorProtocol,
        clock: ClockProtocol,
        max_extract_retries: int = 2,
        extraction_prompt_cfg: dict[str, Any] | None = None,
        extraction_delay_seconds: float = 0.0,
        max_input_tokens: int = 89600,
        extraction_context_chunks_up: int = 1,
        optional_indexer: Optional[Callable[[str], None]] = None,
        metrics: Optional[MetricsRecorder] = None,
    ) -> None:
        self._run_repo = run_repo
        self._document_repo = document_repo
        self._chunk_repo = chunk_repo
        self._action_repo = action_repo
        self._run_event_repo = run_event_repo
        self._storage = storage
        self._parser_factory = parser_factory
        self._chunk_assembler = chunk_assembler
        self._prefilter_service = prefilter_service
        self._llm_adapter = llm_adapter
        self._normalization_config = normalization_config
        self._id_generator = id_generator
        self._clock = clock
        self._max_extract_retries = max_extract_retries
        self._prompt_cfg = extraction_prompt_cfg or {
            "prompt_version": EXTRACTION_PROMPT_VERSION,
            "schema_version": EXTRACTION_SCHEMA_VERSION,
        }
        self._extraction_delay_seconds = max(0.0, extraction_delay_seconds)
        self._max_input_tokens = max_input_tokens
        self._extraction_context_chunks_up = max(0, extraction_context_chunks_up)
        self._optional_indexer = optional_indexer
        self._metrics = metrics

    def execute_run(self, run_id: str, correlation_id: Optional[str] = None) -> None:
        """Run pipeline steps until done or failed. Persists step completion and events."""
        run = self._run_repo.get(run_id)
        if run is None:
            raise NotFoundError(f"Run not found: {run_id}")
        status = (run.status or "").strip().lower()
        if status not in ("queued", "pending", "running"):
            return

        now = self._clock.now()
        if run.started_at is None:
            self._run_repo.update_status(run_id, RunStatus.RUNNING, started_at=now)
        else:
            self._run_repo.update_status(run_id, RunStatus.RUNNING)
        if self._metrics is not None:
            self._metrics.record_run_started()
        log_structured(
            _LOG,
            logging.INFO,
            "run started",
            event="run_started",
            module="run_orchestration",
            run_id=run_id,
            document_id=run.document_id if run else None,
            correlation_id=correlation_id,
        )

        # In-memory context for steps that pass data to the next
        parsed_document: ParsedDocument | None = None
        chunks_in_memory: list[ExtractionChunk] | None = None
        drafts_with_meta: list[Any] = []
        normalized_with_meta: list[Any] = []

        while True:
            run = self._run_repo.get(run_id)
            next_step = self._get_next_step(run)
            if next_step is None:
                break

            # Emit step started or retried (resume path)
            event_type = "retried" if (run and run.current_step == next_step) else "started"
            payload: dict[str, Any] = {}
            if run and run.document_id:
                payload["document_id"] = run.document_id
            self._run_event_repo.append(run_id, next_step, event_type, payload or None)
            step_start = self._clock.now()

            try:
                if next_step == "ingest_ready":
                    self._step_ingest_ready(run_id)
                elif next_step == "parse_document":
                    parsed_document, chunks_in_memory = self._step_parse_document(run_id)
                elif next_step == "build_chunks":
                    if parsed_document is None:
                        parsed_document, chunks_in_memory = self._step_parse_document(run_id)
                    self._step_build_chunks(run_id, parsed_document, chunks_in_memory)
                elif next_step == "prefilter_chunks":
                    self._step_prefilter_chunks(run_id)
                elif next_step == "extract_actions":
                    drafts_with_meta = self._step_extract_actions(run_id)
                elif next_step == "normalize_actions":
                    normalized_with_meta = self._step_normalize_actions(drafts_with_meta)
                elif next_step == "persist_results":
                    self._step_persist_results(run_id, normalized_with_meta)
                elif next_step == "optional_index":
                    if self._optional_indexer is not None:
                        try:
                            self._optional_indexer(run_id)
                        except Exception as e:
                            self._run_repo.update_status(
                                run_id,
                                RunStatus.PARTIAL_SUCCESS,
                                current_step="optional_index",
                            )
                            self._run_event_repo.append(
                                run_id,
                                "optional_index",
                                "partial_success",
                                {"error": str(e)},
                            )
                elif next_step == "complete_run":
                    self._step_complete_run(run_id)
                    run_final = self._run_repo.get(run_id)
                    if self._metrics is not None:
                        if run_final and run_final.status == RunStatus.PARTIAL_SUCCESS:
                            self._metrics.record_run_partial()
                        else:
                            self._metrics.record_run_succeeded()
                    log_structured(
                        _LOG,
                        logging.INFO,
                        "run completed",
                        event="run_completed",
                        module="run_orchestration",
                        run_id=run_id,
                        document_id=run_final.document_id if run_final else None,
                        step="complete_run",
                        correlation_id=correlation_id,
                    )
                    self._run_event_repo.append(run_id, "complete_run", "completed", {})
                    break
            except Exception as e:
                if self._metrics is not None:
                    self._metrics.record_run_failed()
                    if isinstance(e, ParsingError):
                        self._metrics.record_parse_failure()
                    elif isinstance(e, ValidationError):
                        self._metrics.record_extraction_validation_failure()
                err_code = error_code_for_run(e)
                log_structured(
                    _LOG,
                    logging.INFO,
                    "run failed",
                    event="run_failed",
                    module="run_orchestration",
                    run_id=run_id,
                    document_id=run.document_id if run else None,
                    step=next_step,
                    correlation_id=correlation_id,
                )
                self._run_repo.update_status(
                    run_id,
                    RunStatus.FAILED,
                    current_step=next_step,
                    error_code=err_code,
                    error_message=str(e)[:4096],
                    finished_at=self._clock.now(),
                )
                self._run_event_repo.append(run_id, next_step, "failed", {"error": str(e)})
                if is_run_step_retryable(e):
                    raise
                # Re-raise non-retryable so caller can assert (do not mask)
                raise

            # When optional_index failed we already set PARTIAL_SUCCESS and emitted partial_success event
            if next_step == "optional_index":
                run_after = self._run_repo.get(run_id)
                if run_after and run_after.status == RunStatus.PARTIAL_SUCCESS:
                    continue
            if self._metrics is not None:
                elapsed_ms = int((self._clock.now() - step_start).total_seconds() * 1000)
                self._metrics.record_step_latency(next_step, elapsed_ms)
            self._run_repo.update_status(run_id, RunStatus.RUNNING, current_step=next_step)
            self._run_event_repo.append(run_id, next_step, "completed", {})

    def _get_next_step(self, run: Run | None) -> str | None:
        if run is None:
            return None
        current = run.current_step
        if current is None:
            return RUN_PIPELINE_STEPS[0]
        try:
            idx = RUN_PIPELINE_STEPS.index(current)
        except ValueError:
            return RUN_PIPELINE_STEPS[0]
        idx += 1
        if idx >= len(RUN_PIPELINE_STEPS):
            return None
        return RUN_PIPELINE_STEPS[idx]

    def _step_ingest_ready(self, run_id: str) -> None:
        run = self._run_repo.get(run_id)
        if run is None:
            raise NotFoundError(f"Run not found: {run_id}")
        doc = self._document_repo.get(run.document_id)
        if doc is None:
            raise NotFoundError(f"Document not found: {run.document_id}")
        version = self._document_repo.get_version(run.document_version_id)
        if version is None:
            raise NotFoundError(f"Document version not found: {run.document_version_id}")
        parts = getattr(version, "source_parts_jsonb", None) or []
        if parts:
            for part in parts:
                key = part.get("storage_key") if isinstance(part, dict) else None
                if not key:
                    raise StorageNotFoundError("Invalid source_parts entry: missing storage_key")
                try:
                    self._storage.head(key)
                except Exception as e:
                    raise StorageNotFoundError(f"Part not in storage: {key}") from e
        else:
            try:
                self._storage.head(version.source_storage_key)
            except Exception as e:
                raise StorageNotFoundError(f"Source file not in storage: {version.source_storage_key}") from e

    def _step_parse_document(self, run_id: str) -> tuple[ParsedDocument, list[ExtractionChunk]]:
        run = self._run_repo.get(run_id)
        if run is None:
            raise NotFoundError(f"Run not found: {run_id}")
        doc = self._document_repo.get(run.document_id)
        if doc is None:
            raise NotFoundError(f"Document not found: {run.document_id}")
        version = self._document_repo.get_version(run.document_version_id)
        if version is None:
            raise NotFoundError(f"Document version not found: {run.document_version_id}")

        parts = getattr(version, "source_parts_jsonb", None) or []
        num_parts = len(parts) if parts else 1
        log_structured(
            _LOG,
            logging.INFO,
            "Parsing document (%s part(s))" % num_parts,
            run_id=run_id,
            event="parse_document_start",
            module="run_orchestration",
        )
        if parts:
            parsed_list: list[ParsedDocument] = []
            parser = self._parser_factory(run.document_id, run_id)
            for part_idx, part in enumerate(parts):
                key = part.get("storage_key") if isinstance(part, dict) else None
                content_type = (part.get("content_type") or doc.content_type) if isinstance(part, dict) else doc.content_type
                if not key:
                    raise StorageNotFoundError("Invalid source_parts entry: missing storage_key")
                stream = self._storage.get_stream(key)
                body = stream.read()
                parsed_list.append(parser.parse(body, content_type))
                log_structured(
                    _LOG,
                    logging.INFO,
                    "Parsed part %s/%s" % (part_idx + 1, len(parts)),
                    run_id=run_id,
                    event="parse_part_done",
                    module="run_orchestration",
                )
            parsed_document = merge_parsed_documents(run.document_id, run_id, parsed_list)
        else:
            stream = self._storage.get_stream(version.source_storage_key)
            body = stream.read()
            parser = self._parser_factory(run.document_id, run_id)
            parsed_document = parser.parse(body, doc.content_type)
        chunks = self._chunk_assembler.assemble(parsed_document)
        save_parse_artifacts(
            self._storage,
            run.document_id,
            run_id,
            parsed_document,
            chunks,
        )
        return parsed_document, chunks

    def _step_build_chunks(
        self,
        run_id: str,
        parsed_document: ParsedDocument | None,
        chunks_in_memory: list[ExtractionChunk] | None,
    ) -> None:
        if parsed_document is None or chunks_in_memory is None:
            run = self._run_repo.get(run_id)
            if run is None:
                raise NotFoundError(f"Run not found: {run_id}")
            chunks_in_memory = self._chunk_assembler.assemble(parsed_document) if parsed_document else []
        log_structured(
            _LOG,
            logging.INFO,
            "Building chunks (%s chunks)" % len(chunks_in_memory),
            run_id=run_id,
            event="build_chunks",
            module="run_orchestration",
        )
        for c in chunks_in_memory:
            self._chunk_repo.upsert_chunk(
                run_id,
                c.chunk_id,
                c.chunk_text,
                section_path=_section_path_for_repo(c.section_path),
                page_refs=_page_refs_for_repo(c.page_refs),
                estimated_tokens=c.estimated_tokens,
            )

    def _step_prefilter_chunks(self, run_id: str) -> None:
        chunks = self._chunk_repo.list_by_run(run_id)
        if not chunks:
            return
        log_structured(
            _LOG,
            logging.INFO,
            "Doing prefilter (%s chunks)" % len(chunks),
            run_id=run_id,
            event="prefilter_chunks",
            module="run_orchestration",
        )
        extraction_chunks = [_chunk_to_extraction_chunk(c) for c in chunks]
        results: list[PrefilterResult] = self._prefilter_service.score_chunks(extraction_chunks)
        accept = sum(1 for r in results if str(r.decision) == "keep")
        gray = sum(1 for r in results if str(r.decision) == "gray")
        reject = sum(1 for r in results if str(r.decision) == "reject")
        if self._metrics is not None:
            self._metrics.record_prefilter_decisions(accept=accept, gray=gray, reject=reject)
        total = len(chunks)
        for idx, (c, res) in enumerate(zip(chunks, results)):
            decision_str = str(res.decision)
            if decision_str == "keep":
                verdict = "accepted"
            elif decision_str == "reject":
                verdict = "rejected"
            else:
                verdict = "gray_accepted" if res.selected_for_llm else "gray_reject"
            log_structured(
                _LOG,
                logging.INFO,
                "Prefilter chunk %s/%s verdict=%s" % (idx + 1, total, verdict),
                run_id=run_id,
                event="prefilter_chunk",
                module="run_orchestration",
            )
        for c, res in zip(chunks, results):
            self._chunk_repo.upsert_chunk(
                run_id,
                c.chunk_hash,
                c.text or "",
                section_path=c.section_path_jsonb,
                page_refs=c.page_refs_jsonb,
                estimated_tokens=c.estimated_tokens,
                prefilter_score=res.prefilter_score,
                prefilter_decision=str(res.decision),
                prefilter_features=res.to_dict(),
            )

    def _step_extract_actions(self, run_id: str) -> list[Any]:
        all_chunks = self._chunk_repo.list_by_run(run_id)
        selected = self._chunk_repo.list_by_run_for_extraction(run_id)
        out: list[Any] = []
        delay = self._extraction_delay_seconds
        if not selected:
            return out
        expanded = expand_with_context_chunks(
            all_chunks, selected, self._extraction_context_chunks_up
        )
        from app.adapters.llm.prompt_builder import build_extraction_messages_batch
        dummy = ExtractionChunk(
            chunk_id="",
            section_path=[],
            chunk_text="",
            source_spans={},
            page_refs=[],
            estimated_tokens=0,
        )
        system_messages = build_extraction_messages_batch(
            [dummy], "v1", "v1"
        )
        system_prompt_tokens = estimated_tokens(system_messages[0]["content"])
        batches = batch_chunks_for_context(
            expanded,
            self._max_input_tokens,
            system_prompt_tokens,
        )
        log_structured(
            _LOG,
            logging.INFO,
            "Extracting actions: batches (expanded from %s selected chunks), delay between batches"
            % len(selected),
            run_id=run_id,
            batch_count=len(batches),
            extraction_delay_seconds=delay,
            event="extract_actions_start",
        )
        for batch_idx, batch in enumerate(batches):
            if batch_idx > 0 and delay > 0:
                time.sleep(delay)
            ext_chunks = [_chunk_to_extraction_chunk(c) for c in batch]
            log_structured(
                _LOG,
                logging.INFO,
                "LLM batch %s/%s (%s chunks)"
                % (batch_idx + 1, len(batches), len(batch)),
                run_id=run_id,
                event="llm_sent",
                module="run_orchestration",
            )
            try:
                result: ExtractionResult = extract_batch_with_retry(
                    self._llm_adapter,
                    ext_chunks,
                    self._prompt_cfg,
                    self._max_extract_retries,
                )
            except RetryableExternalError as e:
                log_structured(
                    _LOG,
                    logging.WARNING,
                    "Skipping batch %s/%s after retries: %s"
                    % (batch_idx + 1, len(batches), e),
                    run_id=run_id,
                    event="extract_chunk_skipped",
                    module="run_orchestration",
                )
                continue
            log_structured(
                _LOG,
                logging.INFO,
                "LLM batch response %s/%s drafts=%s"
                % (batch_idx + 1, len(batches), len(result.drafts)),
                run_id=run_id,
                event="llm_response",
                module="run_orchestration",
            )
            if self._metrics is not None:
                self._metrics.record_llm_call(
                    cache_hit=result.cache_hit,
                    input_tokens=result.input_tokens,
                    output_tokens=result.output_tokens,
                    estimated_cost=result.estimated_cost_usd,
                )
            batch_hash = build_batch_chunk_hash([c.chunk_hash for c in batch])
            glued_text = BATCH_CHUNK_SEPARATOR.join(c.text or "" for c in batch)
            first = batch[0]
            path_list = (
                first.section_path_jsonb.get("path", [])
                if isinstance(first.section_path_jsonb, dict)
                else (first.section_path_jsonb or [])
            )
            refs_list = (
                first.page_refs_jsonb.get("refs", [])
                if isinstance(first.page_refs_jsonb, dict)
                else (first.page_refs_jsonb or [])
            )
            est_tokens = sum(c.estimated_tokens or 0 for c in batch)
            composite = self._chunk_repo.upsert_chunk(
                run_id,
                batch_hash,
                glued_text,
                section_path=_section_path_for_repo(path_list),
                page_refs=_page_refs_for_repo(refs_list),
                estimated_tokens=est_tokens,
                prefilter_decision=PrefilterDecision.KEEP,
                constituent_chunk_hashes=[c.chunk_hash for c in batch],
            )
            section_path_list = path_list
            page_refs_list = refs_list
            for d in result.drafts:
                out.append((d, composite.id, glued_text, section_path_list, page_refs_list, result))
        return out

    def _step_normalize_actions(self, drafts_with_meta: list[Any]) -> list[Any]:
        """Return list of (NormalizedActionRecord, chunk_id, raw_json, confidence, snippet, section_path, page_refs)."""
        if not drafts_with_meta:
            return []
        draft_list = [t[0] for t in drafts_with_meta]
        records, _ = normalize_batch(draft_list, self._normalization_config)
        out: list[Any] = []
        for rec, (draft, chunk_id, chunk_text, section_path, page_refs, result) in zip(records, drafts_with_meta):
            raw_json = {"raw_response": result.raw_response} if result.raw_response else None
            snippet = (chunk_text or "")[:500]
            out.append((rec, chunk_id, raw_json, None, snippet, section_path, page_refs))
        return out

    def _step_persist_results(self, run_id: str, normalized_with_meta: list[Any]) -> None:
        for item in normalized_with_meta:
            rec, chunk_id, raw_json, confidence, snippet, section_path, page_refs = item
            action, evidence_list = build_action_entities(
                run_id,
                chunk_id,
                rec,
                raw_json=raw_json,
                confidence=confidence,
                id_generator=self._id_generator,
                snippet=snippet,
                section_path=section_path,
                page_refs=page_refs,
            )
            self._action_repo.save(action, evidence=evidence_list)

    def _step_complete_run(self, run_id: str) -> None:
        run = self._run_repo.get(run_id)
        status = RunStatus.PARTIAL_SUCCESS if (run and run.status == RunStatus.PARTIAL_SUCCESS) else RunStatus.SUCCEEDED
        self._run_repo.update_status(
            run_id,
            status,
            current_step="complete_run",
            finished_at=self._clock.now(),
        )
