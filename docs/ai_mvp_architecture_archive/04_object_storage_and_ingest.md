# Module: Object Storage and Ingest

## Goal

Store raw source documents and selected intermediate artifacts durably, with predictable keys, checksums, and recovery behavior.

## Recommended technologies

- S3-compatible object storage
- `boto3` or a minimal S3 client wrapper
- temporary local file staging only when unavoidable

## Storage responsibilities

This module owns:
- upload of raw source files,
- download for worker processing,
- storage of intermediate parse artifacts,
- optional storage of raw LLM responses and debug bundles,
- checksum verification,
- key naming conventions.

## Bucket and key design

Use one bucket with prefixes for MVP:

```text
raw/{document_id}/{version_id}/source.ext
parsed/{document_id}/{run_id}/docling.json
parsed/{document_id}/{run_id}/document.md
llm/{document_id}/{run_id}/{chunk_id}/request.json
llm/{document_id}/{run_id}/{chunk_id}/response.json
debug/{document_id}/{run_id}/...
```

### Rules
- keys must be deterministic,
- no user-controlled path fragments without sanitization,
- never rely on filename uniqueness,
- preserve original filename only as metadata.

## Upload contract

On upload, compute and persist:
- content length,
- MIME type,
- SHA-256 checksum,
- original filename,
- storage key,
- upload timestamp.

The database record is the source of truth; object storage is the artifact store.

## Download contract

Provide methods that:
- stream to temp file,
- stream to bytes for small artifacts,
- verify object existence,
- raise typed internal exceptions.

## Intermediate artifact policy

Persist at least:
- structured parse export,
- serialized extraction chunks,
- optional raw LLM response when debugging or audit mode is enabled.

Do not store every ephemeral intermediate representation by default if it meaningfully raises costs.

## Idempotency policy

Repeated upload of the same logical document can be handled in one of two ways:

### Option A: always create new version
Simpler and safer for MVP.

### Option B: deduplicate on checksum
Lower storage cost but requires stronger policy around versioning and user expectation.

For MVP, prefer **new version per upload** unless storage cost is extreme.

## Failure handling

If database write succeeds but object upload fails:
- mark document as failed ingest,
- do not enqueue processing.

If object upload succeeds but subsequent DB update fails:
- record should be recoverable by a cleanup/reconciliation job.

## Adapter design

Expose a narrow protocol:
- `put_file(...)`
- `put_bytes(...)`
- `get_stream(...)`
- `download_to_tempfile(...)`
- `head(...)`
- `delete(...)` only if lifecycle policy requires it

Wrap vendor exceptions immediately.

## Cost controls

- use lifecycle rules for debug/raw LLM artifacts if enabled,
- keep raw sources long-term,
- keep parse artifacts medium-term,
- keep raw model request/response only in audit/debug mode.

## Acceptance criteria

- uploaded file is durable and retrievable by key,
- checksum is recorded,
- keys are deterministic and inspectable,
- storage failures are visible in run/document status,
- local worker temp files are cleaned up.

## Common pitfalls

- letting API depend on `boto3` details directly,
- storing document bytes in PostgreSQL,
- using original filename as storage key,
- not recording checksum,
- not distinguishing source artifact from derived artifacts.
