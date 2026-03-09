# Module: API Service

## Goal

Expose a minimal HTTP interface for document upload, run creation, status inspection, and result retrieval without embedding heavy processing inside request handlers.

## Recommended technologies

- FastAPI
- Uvicorn / Gunicorn-Uvicorn for serving
- Pydantic request/response models
- request correlation middleware

## Scope of the MVP API

### Write endpoints
- `POST /documents`
- `POST /documents/{document_id}/runs`

### Read endpoints
- `GET /documents/{document_id}`
- `GET /runs/{run_id}`
- `GET /runs/{run_id}/chunks`
- `GET /runs/{run_id}/actions`

### Health endpoints
- `GET /health/live`
- `GET /health/ready`

## Design rules

1. API handlers do not parse documents or call the LLM directly.
2. API handlers are orchestration-only:
   - validate request,
   - persist metadata,
   - upload bytes,
   - enqueue a job,
   - return identifiers and current state.
3. Read endpoints must be pagination-ready even if the initial UI is small.
4. Error responses must be machine-readable.

## Request flow for upload

1. receive multipart file or metadata + remote source reference,
2. validate file size and allowed content type,
3. create document row in PostgreSQL,
4. stream file into object storage,
5. create initial run row or accept explicit run creation separately,
6. enqueue processing job,
7. return `202 Accepted` with identifiers.

## API response policy

Return concise operational data:
- ids,
- status,
- timestamps,
- counters,
- first page of results only if explicitly requested.

Do not return raw parsed document payloads by default.

## FastAPI dependency boundaries

Use dependencies for:
- database session factory / unit-of-work
- authenticated user context if added later
- request id / correlation id injection
- service constructors

Avoid deep dependency graphs that hide control flow.

## File handling

Never load large uploads fully into memory if avoidable.

Use streaming upload path where possible:
- write to temporary file if needed,
- stream to object storage adapter,
- record checksum.

## Validation requirements

Validate:
- filename presence,
- size limits,
- allowed MIME types and extension policy,
- duplicate upload policy,
- explicit idempotency key if supported.

## Status model

Define a public run status enum:
- `queued`
- `running`
- `succeeded`
- `failed`
- `partial_success`
- `cancelled` (reserved)
- `unknown`

Do not expose internal worker step names as the public status contract.

## Security baseline

For MVP:
- internal service token or basic auth if private,
- request size limits,
- no stack traces in responses,
- sanitized filenames,
- rate limiting can be deferred unless public exposure is expected.

## Acceptance criteria

- uploads create durable metadata before queueing work,
- repeated status calls are cheap,
- API never blocks waiting for full extraction,
- handlers remain thin and easy to unit test,
- every response contains correlation identifiers for tracing.

## Common pitfalls

- calling heavy background work from FastAPI `BackgroundTasks` for core ingestion,
- returning giant JSON payloads from read endpoints,
- mixing ORM entities directly into API schemas,
- swallowing queue enqueue failures after file upload.
