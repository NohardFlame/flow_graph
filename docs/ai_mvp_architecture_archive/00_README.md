# AI MVP Architecture Archive

**Python:** Use 3.12 or 3.13. Python 3.14 is not supported (spaCy prefilter pattern matching requires 3.12/3.13).

This archive defines an implementation-ready MVP architecture for a cloud service that:

- accepts multiple source documents,
- parses and restructures them,
- builds extraction-oriented chunks,
- runs a cheap deterministic prefilter before any expensive model call,
- sends only promising chunks to a large model,
- extracts rich action-centric records,
- normalizes keys for later merge/graph building,
- stores source artifacts and structured results,
- keeps the system cheap, testable, and debuggable.

## Design stance

This package is written for a coding agent that must implement the system module-by-module with tests first.

Core principles:

1. **LLM calls are scarce resources.** Spend them only on chunks that already passed deterministic relevance checks.
2. **Action-centric extraction is the primary representation.** Actors, objects, states, permissions, and restrictions live inside each extracted action record.
3. **Parsing and chunking are not retrieval chunking.** Chunks must preserve local business semantics, not merely fit an embedding model.
4. **Normalization is deterministic where possible.** The model may suggest canonical forms, but final canonical keys are computed in code.
5. **Every module has a narrow contract.** Adapters isolate external systems and make mocking straightforward.
6. **Tests should prefer fakes over fragile mocks.** Mock only process boundaries and external I/O.

## Recommended module order

Implement in this order:

1. `02_config_and_project_layout.md`
2. `09_postgres_schema_and_repositories.md`
3. `04_object_storage_and_ingest.md`
4. `05_docling_parse_and_chunking.md`
5. `06_prefilter.md`
6. `07_llm_gateway_and_extraction.md`
7. `08_normalization_and_identity.md`
8. `10_worker_queue_and_runs.md`
9. `03_api_service.md`
10. `12_observability_resilience.md`
11. `13_deployment_and_cloud_mvp.md`
12. `11_qdrant_optional_indexing.md` (optional in first release)

## Suggested repository layout

```text
app/
  api/
  core/
  config/
  db/
  domain/
  services/
  workers/
  adapters/
  tests/
  scripts/
```

## Core external stack

- FastAPI for HTTP API
- ARQ + Redis for background jobs
- PostgreSQL for source-of-truth data
- S3-compatible object storage for raw/intermediate artifacts
- Docling for document conversion and structured parsing
- LiteLLM (SDK or Proxy) for model access, routing, and caching
- Qdrant only as an optional later-stage semantic index

## What the first shipping MVP must prove

- Multiple documents can be uploaded and processed independently.
- Jobs are resumable and idempotent.
- The service stores both raw artifacts and normalized structured outputs.
- Only a subset of chunks reach the expensive model.
- Results are inspectable through API and database queries.
- Failures are visible and recoverable without manual database surgery.

Additional guide:
- `00_MASTER_IMPLEMENTATION_ORDER.md` — strict implementation order, dependencies, stop/go criteria, and coding rhythm
