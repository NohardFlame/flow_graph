# Module: PostgreSQL Schema and Repositories

## Goal

Define the source-of-truth relational schema, migration strategy, repository interfaces, and transaction rules for the MVP.

## Recommended technologies

- PostgreSQL
- SQLAlchemy 2
- Alembic
- `jsonb` for raw extraction payloads and selected diagnostics

## Core rule

The relational database is the authoritative state store for:
- documents,
- runs,
- chunks,
- extracted actions,
- processing events,
- failures,
- metrics references.

## Proposed tables

### `documents`
- `id`
- `original_filename`
- `content_type`
- `checksum_sha256`
- `size_bytes`
- `storage_key`
- `created_at`

### `document_versions`
- `id`
- `document_id`
- `version_number`
- `source_storage_key`
- `created_at`

### `runs`
- `id`
- `document_id`
- `document_version_id`
- `status`
- `current_step`
- `error_code`
- `error_message`
- `started_at`
- `finished_at`
- `config_version`

### `parsed_artifacts`
- `id`
- `run_id`
- `docling_storage_key`
- `markdown_storage_key`
- `chunk_manifest_storage_key`

### `chunks`
- `id`
- `run_id`
- `chunk_hash`
- `section_path_jsonb`
- `page_refs_jsonb`
- `text`
- `estimated_tokens`
- `prefilter_score`
- `prefilter_decision`
- `prefilter_features_jsonb`

### `llm_calls`
- `id`
- `run_id`
- `chunk_id`
- `provider`
- `model`
- `prompt_version`
- `schema_version`
- `cache_hit`
- `retry_count`
- `latency_ms`
- `input_tokens`
- `output_tokens`
- `estimated_cost_usd`
- `request_storage_key`
- `response_storage_key`

### `actions`
- `id`
- `run_id`
- `chunk_id`
- `action_label`
- `action_canonical`
- `primary_actor_key`
- `primary_object_key`
- `input_state_key`
- `output_state_key`
- `confidence`
- `raw_jsonb`
- `normalization_version`

### `action_evidence`
- `id`
- `action_id`
- `snippet`
- `section_path_jsonb`
- `page_refs_jsonb`

### `run_events`
- `id`
- `run_id`
- `step`
- `event_type`
- `payload_jsonb`
- `created_at`

## Schema design rules

1. Every downstream table must reference `run_id`.
2. Use `jsonb` for flexible payloads, but also promote frequently queried fields to first-class columns.
3. Prefer explicit status enums or constrained text fields.
4. Use deterministic unique constraints where idempotency matters:
   - `(run_id, chunk_hash)` for chunks,
   - optional uniqueness on LLM call identity if caching/persistence requires it.

## Repository design

Define narrow repositories:
- `DocumentRepository`
- `RunRepository`
- `ChunkRepository`
- `LLMCallRepository`
- `ActionRepository`
- `RunEventRepository`

Repositories should expose domain operations, not generic CRUD dumping.

## Session and transaction policy

Use one transaction per service operation or worker step boundary, not one giant transaction over the full pipeline.

Never share one SQLAlchemy session across concurrent tasks.

## Migration policy

- Use Alembic for all schema changes.
- Autogenerate only as a draft; review migrations manually.
- Store migration history in repo.

## Idempotency strategy

Worker step reruns must not duplicate chunk/action rows.

Use one or more of:
- deterministic hashes,
- unique constraints,
- upsert patterns,
- repository-level "insert if absent" methods.

## Acceptance criteria

- schema supports full run audit trail,
- common read paths do not require parsing giant JSON blobs,
- migrations are reviewable,
- reruns do not create silent duplicates,
- repository methods map cleanly to domain actions.

## Common pitfalls

- storing everything only in JSON,
- generic repository abstractions that hide useful queries,
- one giant transaction across parsing, LLM, and persistence,
- relying solely on ORM convenience without idempotency constraints.
