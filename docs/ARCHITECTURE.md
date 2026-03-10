# Flow-Graph Application Architecture

This document describes the architecture of the **flow-graph** application as implemented in code. It is written from a system-design perspective and does not rely on external design docs.

---

## 1. Executive Summary

**Flow-graph** is a document-processing pipeline that:

1. Accepts document uploads (PDF, DOC, DOCX, TXT, MD).
2. Parses documents into a structured representation (sections, tables, lists).
3. Chunks content for extraction, scores chunks via a prefilter (keep/gray/reject), and sends accepted chunks to an LLM to extract **actions** (verb, actor, object, states).
4. Normalizes extracted actions to canonical keys (slugs, aliases, reserved checks) and persists them with evidence.
5. Exposes runs, chunks, and actions via a REST API and supports optional indexing (e.g. Qdrant).

The system is built as a **layered, adapter-based** design: API and workers depend on protocols; concrete storage, queue, parser, and LLM implementations are swappable. Configuration is environment-driven and immutable after load. No service locator: dependencies are injected via constructors or FastAPI `Depends`.

---

## 2. High-Level Architecture

```
                    ┌─────────────────────────────────────────────────────────┐
                    │                     API (FastAPI)                        │
                    │  /documents (upload, get)  /documents/{id}/runs (create)  │
                    │  /runs/{id}  /runs/{id}/chunks  /runs/{id}/actions        │
                    │  /health/live  /health/ready                              │
                    └───────────────────────────┬───────────────────────────────┘
                                                │
              ┌─────────────────────────────────┼─────────────────────────────────┐
              │                                 │                                 │
              ▼                                 ▼                                 ▼
    ┌─────────────────┐              ┌─────────────────────┐            ┌─────────────────┐
    │ Object Storage  │              │   Job Queue (ARQ)   │            │   PostgreSQL    │
    │ (S3-compatible) │              │   Redis-backed      │            │   (system of    │
    │ or Fake         │              │   or Fake           │            │    record)      │
    └────────┬────────┘              └──────────┬──────────┘            └────────┬────────┘
             │                                   │                                │
             │         Worker process             │                                │
             │    ┌───────────────────────────────┴───────────────────────────────┐│
             │    │                  RunOrchestrator                              ││
             └────┼──► ingest_ready → parse → build_chunks → prefilter → extract   ││
                  │         → normalize → persist_results → optional_index → done ││
                  │    (storage, parser, chunk_assembler, prefilter, LLM, norm)   ││
                  └──────────────────────────────────────────────────────────────┘│
                                                                                   │
                  External: Docling (parser), LiteLLM (LLM), optional Qdrant        │
                                                                                   ▼
                                                                           Repositories
                                                                           (Session-scoped)
```

- **API**: Synchronous HTTP; one transaction per request (session per request, commit on success).
- **Worker**: One process (ARQ) pulls jobs from Redis; each job runs the full pipeline in a **single DB session** (commit on success, rollback on failure). Retryability is determined by exception type.

---

## 3. Layer Overview

| Layer | Responsibility | Key Modules |
|-------|----------------|-------------|
| **API** | HTTP entrypoints, validation, error mapping, correlation ID | `app.api` (main, app, deps, routes, schemas, wiring) |
| **Services** | Use-case orchestration and domain logic | `app.services` (ingest, run_orchestration, prefilter, normalization, chunk_assembler, parse_artifact, action_persistence) |
| **Domain** | Data shapes and value types (no I/O) | `app.domain` (extraction_models, normalization_models, parse_models) |
| **Adapters** | External I/O behind protocols | `app.adapters` (storage, queue, parser, llm) |
| **Persistence** | DB models and repositories | `app.db` (models, session, repositories) |
| **Core** | Protocols, errors, constants, storage keys, normalization helpers, metrics protocol | `app.core` |
| **Config** | Environment-based settings (single source) | `app.config` (settings, logging) |
| **Workers** | Queue consumer and pipeline invocation | `app.workers` (arq_tasks, tasks, deps, retry_policy, schemas) |

Services and API do not import adapter implementations directly where avoidable; they depend on **protocols** defined in `app.core.protocols`. Wiring (which implementation to use) is done at composition roots: `app.api.wiring` (API) and `app.workers.deps` (worker).

---

## 4. Configuration

- **Single source**: All configuration is loaded from the environment via `app.config.settings`. Only this package reads `os.environ` for app config.
- **Root object**: `Settings` (Pydantic `BaseSettings`) is **frozen** and validated at startup. Nested groups use `env_prefix` (e.g. `APP_`, `API_`, `POSTGRES_`, `REDIS_`, `S3_`, `LITELLM_`, `PREFILTER_`, `NORMALIZATION_`, `WORKER_`, `QDRANT_`, `OBS_`).
- **Required**: `environment` (e.g. `APP_ENVIRONMENT` or `ENVIRONMENT`) is required.
- **Feature flags**: `use_fake_adapters` (in-memory storage/queue), `enable_qdrant`, `enable_llm_cache`, `enable_prefilter_debug_fields`.
- **Caching**: `get_settings()` is cached (no overrides); tests can call `reset_settings_cache()` before changing env.

Relevant settings groups:

- **Api**: host, port, max_upload_bytes, allowed_extensions, allowed_content_types.
- **Postgres**: host, port, user, password, db → `dsn`.
- **Redis**: url (for ARQ).
- **S3**: endpoint_url, bucket, key_prefix.
- **Docling**: enabled.
- **LiteLLM**: api_key, model, base_url, fallback_model, max_retries, request_timeout, repair_max_attempts.
- **Prefilter**: thresholds (accept/gray), weights per feature group, lexicon_dir, spacy_model, enable_pattern_matching, gray policy (top_gray_budget_per_document, gray_adjacent_to_accepted).
- **Normalization**: config_dir, normalization_version.
- **Worker**: concurrency, queue_name.
- **Observability**: log_level, enable_debug_artifacts, step_timeout_seconds.

---

## 5. API Layer

### 5.1 Entrypoint and App Factory

- **ASGI entry**: `app.api.main` builds storage and queue via `wiring.get_storage()` / `wiring.get_queue()`, gets a session factory from `app.db.session.get_session_factory()`, and calls `app.api.app.create_app(storage, queue, session_factory)`.
- **create_app(storage, queue, session_factory, metrics)**:
  - Creates FastAPI app, adds `CorrelationIdMiddleware` (X-Request-ID).
  - Attaches to `app.state`: `storage`, `queue`, `session_factory`, `metrics` (default `NoOpMetricsRecorder`).
  - Registers routers: documents, runs, health.
  - Registers exception handlers for `NotFoundError`, `ValidationError`, `ConflictError`, `StorageError`, `DomainError` → JSON body with `detail`, `code`, `correlation_id`.

### 5.2 Wiring (Adapter Selection)

- **Storage**: If `use_fake_adapters`: `FakeObjectStorage`; else `S3ObjectStorage(settings.s3)`.
- **Queue**: If `use_fake_adapters`: `FakeJobQueue`; else `ARQJobQueue` (Redis from settings).

### 5.3 Dependencies (app.api.deps)

- **get_db_session**: Yields a DB session; commits on success (unless `request.app.state.commit_db` is False), rollback on exception, always close.
- **get_storage**, **get_queue**: From `request.app.state`.
- **get_document_repo**, **get_run_repo**, **get_chunk_repo**, **get_action_repo**, **get_run_event_repo**: Repository instances bound to the request session.
- **get_ingest_service**: `IngestService(storage, document_repo)`.
- **get_metrics**: From `request.app.state`.

### 5.4 Routes

- **Documents** (`/documents`):
  - `POST ""`: Upload file → validate size/extension/content-type → `IngestService.ingest()` → persist document and first version, return 201 with document id and metadata. Does **not** create a run.
  - `GET "/{document_id}"`: Return document metadata or 404.
  - `POST "/{document_id}/runs"`: Ensure document and latest version exist, ensure no active run (pending/queued/running) → create `Run` (status `queued`), save, enqueue payload `{ run_id, correlation_id? }`, return 202.
- **Runs** (`/runs`):
  - `GET "/{run_id}"`: Run status (internal status mapped to `PublicRunStatus`), timestamps, error_message, error_code, current_step.
  - `GET "/{run_id}/events"`: Ordered run events (step, event_type, created_at, payload).
  - `GET "/{run_id}/chunks"`: Paginated chunks (id, chunk_hash, text, estimated_tokens, prefilter_decision).
  - `GET "/{run_id}/actions"`: Paginated actions (id, action_label, action_canonical, confidence).
- **Health** (`/health`):
  - `GET /live`: Always 200.
  - `GET /ready`: 200 if DB (and Redis when queue has `ping`) are OK; 503 with checks dict otherwise.

### 5.5 Schemas and Errors

- **Schemas** (`app.api.schemas`): Pydantic models for responses and public enums (`PublicRunStatus`). Internal run status is mapped to public in one place (`internal_status_to_public`). Error response: `detail`, `code`, optional `correlation_id`.
- **Errors** (`app.core.errors`): Hierarchy under `DomainError`: `ConfigError`, `ValidationError`, `RetryableExternalError`, `PermanentExternalError`, `ParsingError`, `ExtractionError`, `NormalizationError`, `StorageError` (and `StorageNotFoundError`), `NotFoundError`, `ConflictError`, `InternalError`. Handlers map these to HTTP status and JSON body.

---

## 6. Service Layer

### 6.1 IngestService

- **Role**: Upload raw bytes to object storage, then persist `Document` and first `DocumentVersion`.
- **Input**: body (bytes), original_filename, content_type.
- **Steps**: Generate document_id and version_id; compute SHA-256 checksum; build storage key via `raw_source_key(document_id, version_id, content_type)`; `storage.put_bytes(...)`; create `Document` and optionally first `DocumentVersion` via `document_repo.save(..., create_first_version=True, source_storage_key=key)`.
- **Dependencies**: `ObjectStorageProtocol`, document repository, optional `IdGeneratorProtocol`. Filename is sanitized (no path/control chars); key derivation uses content_type only, not user filename.

### 6.2 RunOrchestrator (Run Pipeline)

- **Role**: Execute the document-processing pipeline for a single run in order; persist step progress and events; support resume by re-reading run state.
- **Steps** (from `RUN_PIPELINE_STEPS` in `app.core.constants`):
  1. **ingest_ready**: Verify document and version exist and source object exists in storage (`storage.head`).
  2. **parse_document**: Load source from storage, call parser (e.g. Docling), get `ParsedDocument`; run `ChunkAssembler.assemble(parsed_document)`; call `save_parse_artifacts` (docling export, chunk manifest, optional markdown) to storage.
  3. **build_chunks**: Upsert chunks to DB (idempotent by `run_id` + `chunk_hash`); section_path and page_refs stored as JSONB.
  4. **prefilter_chunks**: Load chunks, convert to `ExtractionChunk`, call `PrefilterService.score_chunks`; persist back prefilter_score, prefilter_decision, prefilter_features per chunk.
  5. **extract_actions**: Load chunks with decision `keep`; for each, call `extract_with_retry(llm_adapter, chunk, prompt_cfg, max_retries)`; collect (draft, chunk_id, text, section_path, page_refs, result).
  6. **normalize_actions**: `normalize_batch(drafts, normalization_config)` → list of `NormalizedActionRecord`; attach chunk/snippet/section_path/page_refs for persistence.
  7. **persist_results**: For each normalized record, `build_action_entities(...)` → Action + ActionEvidence; `action_repo.save(action, evidence=...)` (upsert by run_id + action_canonical).
  8. **optional_index**: If `optional_indexer` is set, call it (e.g. index to Qdrant); on failure set run status to PARTIAL_SUCCESS and emit event, do not fail the run.
  9. **complete_run**: Set run status to SUCCEEDED (or PARTIAL_SUCCESS if optional_index failed), set finished_at.

- **State**: Run status and `current_step` are updated after each step; on exception, run is marked FAILED with error_code and error_message, and an event is appended. Next step is derived from `current_step` index in `RUN_PIPELINE_STEPS`; when the loop advances, the orchestrator can resume from the next step on retry.
- **Dependencies**: RunRepository, DocumentRepository, ChunkRepository, ActionRepository, RunEventRepository, ObjectStorageProtocol, parser_factory(document_id, run_id), ChunkAssembler, PrefilterService, LLM adapter (ExtractActionsProtocol), NormalizationConfig, IdGenerator, Clock, optional indexer, optional MetricsRecorder.

### 6.3 ChunkAssembler

- **Role**: Turn `ParsedDocument` into a list of `ExtractionChunk` with deterministic `chunk_id` (SHA-256 of path+text+index).
- **Logic**: Group section units by semantic affinity (heading+paragraph, table+paragraph, list+list, etc.); respect token target (e.g. 1500–4000); split by subheading or by token count when over target; optional overlap with previous heading for context. Each chunk gets section_path, chunk_text, source_spans, page_refs, estimated_tokens, structural_features (has_table, has_list, section_depth).

### 6.4 PrefilterService

- **Role**: Score chunks and assign decision (keep / gray / reject) with explainability.
- **Features**: Structural (heading relevance, table/list, depth, appendix penalty), exact lexicon matches, pattern matching (e.g. spaCy), context boost (action/object/role/state terms), lexical (seeded queries). Weights and thresholds come from settings; gray-zone policy (e.g. top N gray per document, gray adjacent to accepted) is applied after scoring.
- **Output**: List of `PrefilterResult` (prefilter_score, decision, feature_breakdown, matched_terms, matched_patterns, structural_flags, lexical_score, selected_for_llm).

### 6.5 Normalization (normalization_service)

- **Role**: Map LLM output (`ExtractionDraft`) to canonical keys and produce `NormalizedActionRecord`.
- **Steps**: Transliterate → slugify → resolve alias (verb/object/actor/state from config) → check reserved → build keys (e.g. `build_action_key(verb_slug, object_key)`). Warnings and collisions (multiple surface forms → same canonical) are collected. `normalize_batch` also detects collisions across drafts.

### 6.6 Parse Artifact Service

- **Role**: Write parse and chunk artifacts to object storage for debugging (docling summary, chunk_manifest, optional markdown) using `parsed_artifact_key(document_id, run_id, artifact)`.

### 6.7 Action Persistence (action_persistence)

- **Role**: Build `Action` and `ActionEvidence` entities from `NormalizedActionRecord` (snippet, section_path, page_refs) for repository save. Idempotency is enforced at repository level (upsert by run_id + action_canonical).

---

## 7. Domain Models

- **extraction_models**: `ExtractionResult` (drafts, provider, model, prompt_version, schema_version, cache_hit, retry_count, latency_ms, tokens, cost, warnings, fallback_used, structured_output_used, schema_fallback_used, raw_response, repaired_response); `RepairResult` (repaired_json, success, drafts).
- **normalization_models**: `ExtractionDraft` (verb, primary_object, primary_actor, input_state, output_state, action_label, suggested_*_canonical); `NormalizedActionRecord` (action_canonical, primary_actor_key, primary_object_key, input_state_key, output_state_key, surface_forms, suggested_canonical, aliases, warnings, collisions, normalization_version); `CollisionRecord`.
- **parse_models**: `BlockType`, `SectionUnit`, `ParsedDocument` (document_id, run_id, source_format, title, sections, tables, lists); `ExtractionChunk` (chunk_id, section_path, chunk_text, source_spans, page_refs, estimated_tokens, structural_features).

Domain types are used across services and adapters; they do not carry ORM or I/O.

---

## 8. Adapters

### 8.1 Storage

- **ObjectStorageProtocol** (`app.core.protocols`): put_bytes, put_file, get_stream, download_to_tempfile, head, delete.
- **S3ObjectStorage**: boto3 S3 client; maps ClientError/BotoCoreError to `StorageNotFoundError`, `RetryableExternalError`, `PermanentExternalError`. Key prefix from settings.
- **FakeObjectStorage**: In-memory dict; used when `use_fake_adapters` or in tests.

### 8.2 Queue

- **JobQueueProtocol**: `enqueue(payload)`. Optional `ping()` for readiness.
- **ARQJobQueue**: Uses ARQ to enqueue job `process_run_job` to Redis; payload must include `run_id`. Enqueue runs in a sync context via run_until_complete.
- **FakeJobQueue**: In-memory list of payloads.

### 8.3 Parser

- **DocumentParserProtocol**: `parse(source: bytes | str, content_type?) -> ParsedDocument`.
- **DoclingParserAdapter**: Uses Docling `DocumentConverter`; supports file (bytes) and string (markdown/HTML). Maps Docling output to `ParsedDocument` (SectionUnit list, block types, page_refs). Raises `ParsingError` on failure.

### 8.4 LLM

- **LLMClientProtocol**: `extract_actions(chunk, prompt_cfg) -> ExtractionResult`; `repair_json(raw_output, schema_cfg) -> RepairResult`. Implementations must map provider exceptions to domain errors (RetryableExternalError, PermanentExternalError, ExtractionError).
- **LiteLLMAdapter**: Builds messages via `build_extraction_messages`; calls LiteLLM completion with optional JSON schema (structured output); on parse failure can call `repair_json` (one short repair call). Handles timeouts, rate limits, auth/bad-request; supports fallback model and retries.
- **FakeLLMAdapter**: Returns configurable list of drafts (e.g. empty) without calling any API.
- **extract_with_retry** (retry_repair): Wraps `extract_actions` and retries on `RetryableExternalError` up to max_retries.

Storage keys for LLM artifacts use `llm_artifact_key(document_id, run_id, chunk_id, kind)` (request/response); prompt/schema versions and normalization config drive cache keys when LLM cache is enabled.

---

## 9. Persistence Layer

### 9.1 Database and Session

- **Engine**: Created from `Settings.postgres.dsn` (postgresql+psycopg); pool_pre_ping.
- **Session**: Session factory (autocommit=False, autoflush=False, expire_on_commit=False). One transaction per operation: API uses request-scoped session (commit on success); worker uses one session per job (commit after full pipeline success).

### 9.2 Models (SQLAlchemy 2 declarative)

- **Document**: id, original_filename, content_type, checksum_sha256, size_bytes, storage_key, created_at; relationship to DocumentVersion.
- **DocumentVersion**: id, document_id, version_number, source_storage_key, created_at.
- **Run**: id, document_id, document_version_id, status, current_step, error_code, error_message, started_at, finished_at, config_version; relationships to ParsedArtifact, Chunk, LLMCall, Action, RunEvent.
- **ParsedArtifact**: id, run_id, docling_storage_key, markdown_storage_key, chunk_manifest_storage_key.
- **Chunk**: id, run_id, chunk_hash, section_path_jsonb, page_refs_jsonb, text, estimated_tokens, prefilter_score, prefilter_decision, prefilter_features_jsonb; unique (run_id, chunk_hash).
- **LLMCall**: id, run_id, chunk_id, provider, model, prompt_version, schema_version, cache_hit, retry_count, latency_ms, input/output_tokens, estimated_cost_usd, request/response_storage_key.
- **Action**: id, run_id, chunk_id, action_label, action_canonical, primary_actor_key, primary_object_key, input_state_key, output_state_key, confidence, raw_jsonb, normalization_version; relationship to ActionEvidence.
- **ActionEvidence**: id, action_id, snippet, section_path_jsonb, page_refs_jsonb.
- **RunEvent**: id, run_id, step, event_type, payload_jsonb, created_at.

Migrations: Alembic (e.g. `alembic/versions/001_baseline_schema.py`).

### 9.3 Repositories

- **DocumentRepository**: get, get_version, get_latest_version, save (with optional create_first_version + source_storage_key).
- **RunRepository**: get, get_active_run_for_document (pending/queued/running), save, update_status(run_id, status, **kwargs).
- **ChunkRepository**: upsert_chunk (on conflict update by run_id+chunk_hash), list_by_run (with limit/offset), count_by_run, list_by_run_and_decision(decision).
- **ActionRepository**: get, save(action, evidence=...) with upsert by (run_id, action_canonical); list_by_run, count_by_run.
- **RunEventRepository**: append(run_id, step, event_type, payload), list_by_run.
- **LLMCallRepository**: Used for audit; save, get, list_by_run.

All repositories take a `Session` in the constructor; no global session.

---

## 10. Worker Layer

- **ARQ entry**: `app.workers.arq_tasks` defines `process_run_job` (async) which runs `process_run_job_sync(payload)` in a thread pool executor. `WorkerSettings` points ARQ at this task and configures Redis and max_jobs from settings.
- **process_run_job_sync** (`app.workers.tasks`): Deserializes payload to `RunJobPayload` (run_id, optional document_id, attempt, correlation_id); obtains session from factory and orchestrator from `build_orchestrator(session)`; runs `orchestrator.execute_run(run_id, correlation_id)`; commits on success, rollback on failure; re-raises if `is_run_step_retryable(exc)` so ARQ can retry.
- **build_orchestrator** (`app.workers.deps`): Builds RunOrchestrator with repositories bound to the given session and shared deps from `get_worker_deps()`: storage (S3 or Fake), parser_factory (Docling), ChunkAssembler, PrefilterService (lexicon_dir from settings), LLM adapter (LiteLLM if api_key set, else Fake), normalization_config (from config_dir), id_generator, clock, max_extract_retries, extraction_prompt_cfg. Optional indexer is not wired in deps by default.

**Retry policy** (`app.workers.retry_policy`): `is_run_step_retryable(exc)` returns True for RetryableExternalError and generic StorageError (and certain stdlib errors); False for ValidationError, ConfigError, PermanentExternalError, ParsingError, NormalizationError, ExtractionError, NotFoundError, StorageNotFoundError, InternalError. `error_code_for_run(exc)` returns a short string for run.error_code.

---

## 11. Core Utilities

- **protocols**: ObjectStorageProtocol, JobQueueProtocol, DocumentParserProtocol, LLMClientProtocol, VectorIndexProtocol, RunRepositoryProtocol, DocumentRepositoryProtocol, ActionRepositoryProtocol, ChunkRepositoryProtocol, LLMCallRepositoryProtocol, RunEventRepositoryProtocol, ClockProtocol, IdGeneratorProtocol.
- **errors**: DomainError hierarchy (see §5.5).
- **constants**: RunStatus, RUN_PIPELINE_STEPS, JobStatus, PrefilterDecision, EXTRACTION_PROMPT_VERSION, EXTRACTION_SCHEMA_VERSION.
- **storage_keys**: Deterministic key builders (raw_source_key, parsed_artifact_key, llm_artifact_key, debug_prefix); segment validation to prevent path escape; extension from content_type only.
- **types**: DocumentId, RunId, ChunkId, JobId, ActionId; ObjectMetadata.
- **metrics**: MetricsRecorder protocol (document_uploaded, run_started/succeeded/failed/partial, prefilter_decisions, llm_call, parse_failure, extraction_validation_failure, step_latency); InMemoryMetricsRecorder and NoOpMetricsRecorder.

Normalization helpers (slugify, transliterate, reserved check, key builders) and NormalizationConfig (load from config dir, resolve_verb/object/role/state) live under `app.core.normalization` and `app.core.normalization_config`.

---

## 12. Data Flow Summary

1. **Upload**: Client → POST /documents (file) → IngestService → storage.put_bytes + document_repo.save (document + first version) → 201.
2. **Start run**: Client → POST /documents/{id}/runs → check document/version, no active run → Run created (queued) → queue.enqueue({ run_id, correlation_id }) → 202.
3. **Worker**: ARQ picks job → process_run_job_sync → session + RunOrchestrator.execute_run(run_id) → ingest_ready → parse_document (storage.get_stream, parser.parse, ChunkAssembler, save_parse_artifacts) → build_chunks (chunk_repo.upsert_chunk) → prefilter_chunks (PrefilterService, upsert prefilter fields) → extract_actions (LLM per keep-chunk, extract_with_retry) → normalize_actions (normalize_batch) → persist_results (build_action_entities, action_repo.save) → optional_index → complete_run → session.commit (or rollback and re-raise if retryable).
4. **Read**: GET /runs/{id}, /runs/{id}/chunks, /runs/{id}/actions use repositories with same session pattern; status mapped to PublicRunStatus.

---

## 13. Design Decisions (Summary)

- **Protocol-based adapters**: Storage, queue, parser, LLM are abstracted; fakes allow local and test runs without S3/Redis/LLM.
- **Single transaction per run**: Worker runs the whole pipeline in one session; commit only on full success. Simplifies consistency and retry (re-run from start or resume by step).
- **Step-based resume**: Run.current_step and RUN_PIPELINE_STEPS allow the orchestrator to skip already-done steps on retry (e.g. after parse_document, next step is build_chunks).
- **Idempotent writes**: Chunks upsert by (run_id, chunk_hash); actions upsert by (run_id, action_canonical). Safe to re-run or replay.
- **No config in domain**: Domain and services receive config or settings via constructors; no direct env access outside config.
- **Structured errors**: All external failures mapped to domain exceptions; API and worker map to HTTP and retry behavior in one place.
- **Correlation ID**: Passed from API to queue payload and into orchestrator for logging/tracing.
- **Keys from IDs and content_type only**: Storage keys avoid user-controlled filenames; safe segments and content-type-derived extensions.

This architecture supports scaling the worker horizontally (multiple ARQ workers), swapping storage/queue/LLM per environment, and testing each layer with fakes and unit tests without touching the core pipeline logic.
