# Master Implementation Order

This file defines the **actual implementation sequence** for the MVP.

The goal is to keep the coding agent from building modules in an order that creates unnecessary blockers, unstable tests, or premature integration work. The sequence below is dependency-driven and optimized for **test-first implementation**.

---

## Core principles

1. **Implement contracts before integrations.**
   Start from config, schemas, interfaces, and repositories before wiring workers and external services.

2. **Prefer vertical completion at each phase.**
   Each phase should end with something executable and testable, not just partially defined abstractions.

3. **Write tests first for each module, but not all tests for the whole system at once.**
   The agent should read the module spec and its matching test spec together, then implement only that slice.

4. **Defer optional modules.**
   Qdrant, advanced observability, and cloud-hardening should not block the first end-to-end run.

5. **No LLM integration before deterministic preprocessing exists.**
   The LLM should sit on top of stable inputs: parsed documents, assembled chunks, prefilter scores, and validated persistence.

---

## Reading order for the coding agent

Before coding, read these files in this order:

1. `00_README.md`
2. `01_architecture_overview.md`
3. `00_MASTER_IMPLEMENTATION_ORDER.md`
4. Then, for each phase below, read the implementation file and its matching test file together.

---

## Phase 0 — Foundation and repository skeleton

### Implement
- `02_config_and_project_layout.md`
- `02_tests_config_and_project_layout.md`

### Goal
Establish the project skeleton, dependency injection approach, environment-driven settings, module boundaries, base typing conventions, and common utilities.

### Why first
Every other module depends on stable configuration, import layout, and shared contracts.

### Required outputs
- app package structure exists
- settings model loads from environment
- test layout mirrors source layout
- common protocol/interface locations are created
- base exception hierarchy is defined
- shared IDs / enums / constants modules exist

### Stop/go criteria
Move to the next phase only if:
- configuration can be loaded in tests without real cloud credentials
- imports are stable and circular dependencies are avoided
- base fixtures for tests exist

---

## Phase 1 — Database schema and repository layer

### Implement
- `09_postgres_schema_and_repositories.md`
- `09_tests_postgres_schema_and_repositories.md`

### Goal
Create the system of record for documents, runs, chunks, actions, raw extraction payloads, and statuses.

### Why now
All orchestration and processing stages need a place to persist state. Repositories should be stable before API and worker logic are written.

### Required outputs
- SQLAlchemy models or Core tables created
- Alembic baseline migration created
- repository interfaces and concrete implementations created
- transaction boundaries defined
- test database fixtures working

### Stop/go criteria
Move on only if:
- migrations apply cleanly from empty state
- repositories pass CRUD and idempotency tests
- run/document/chunk/action relationships are stable
- raw JSON payload storage works

---

## Phase 2 — Object storage and ingest persistence

### Implement
- `04_object_storage_and_ingest.md`
- `04_tests_object_storage_and_ingest.md`

### Goal
Support upload persistence for original source files and derived artifacts.

### Why here
The pipeline starts from files. Before API and workers, storage contracts must already exist and be testable.

### Required outputs
- storage interface
- S3-compatible implementation
- deterministic object key strategy
- upload/download/delete methods
- content metadata handling
- local or fake storage test implementation

### Stop/go criteria
Move on only if:
- uploads can be tested without real cloud storage
- object key generation is deterministic
- storage failures map to domain exceptions

---

## Phase 3 — API service shell

### Implement
- `03_api_service.md`
- `03_tests_api_service.md`

### Goal
Provide the minimum HTTP surface for file submission, run creation, status retrieval, and result retrieval.

### Why before parser/worker
You want a stable entrypoint early, but the handlers should remain thin and delegate to services/repositories.

### Required outputs
- upload endpoint
- create-run endpoint
- get-run-status endpoint
- get-document-actions endpoint
- dependency injection wiring
- request/response schemas

### Stop/go criteria
Move on only if:
- endpoints run against test database + fake storage
- API tests do not require real parser, queue, or LLM
- invalid inputs and failure paths are covered

---

## Phase 4 — Docling parsing and chunk assembly

### Implement
- `05_docling_parse_and_chunking.md`
- `05_tests_docling_parse_and_chunking.md`

### Goal
Convert documents into structured parse output and then assemble extraction-oriented chunks.

### Why here
The entire pipeline quality depends on chunk assembly. It must be deterministic and testable before queue orchestration or LLM extraction are introduced.

### Required outputs
- parser adapter wrapping Docling
- parse result normalization into internal structures
- section-aware chunk assembler
- table/list-aware grouping rules
- token estimate logic
- chunk metadata model

### Stop/go criteria
Move on only if:
- the same input produces stable chunk boundaries
- chunk assembly can be tested from fixture documents
- parser adapter failures are isolated behind domain exceptions
- no LLM is needed to validate chunking correctness

---

## Phase 5 — Deterministic prefilter

### Implement
- `06_prefilter.md`
- `06_tests_prefilter.md`

### Goal
Rank or gate chunks before LLM extraction using deterministic signals.

### Why before LLM
This is the main token-saving mechanism. It must exist before the LLM pipeline is integrated, otherwise the system will be over-expensive by construction.

### Required outputs
- feature extraction for structural signals
- phrase/alias matching
- rule-based pattern scoring
- context boosts
- final relevance score or tier
- explicit decision bands: keep / gray / reject

### Stop/go criteria
Move on only if:
- prefilter behavior is reproducible and explainable
- score breakdown is available for debugging
- false positive / false negative fixture coverage exists
- chunk gating can run without network access

---

## Phase 6 — Normalization and identity

### Implement
- `08_normalization_and_identity.md`
- `08_tests_normalization_and_identity.md`

### Goal
Create deterministic canonical keys for actors, objects, actions, and states.

### Why before LLM wiring
The extraction pipeline should know what normalized output format it targets. Also, repository upserts depend on canonical identity strategy.

### Required outputs
- normalization utilities
- canonical key builders
- alias preservation logic
- collision policy
- deterministic slug rules

### Stop/go criteria
Move on only if:
- normalization is deterministic across platforms
- canonical keys are stable in tests
- obvious collisions are handled explicitly

---

## Phase 7 — LLM gateway and extraction contracts

### Implement
- `07_llm_gateway_and_extraction.md`
- `07_tests_llm_gateway_and_extraction.md`

### Goal
Add the model integration only after deterministic inputs and persistence layers are stable.

### Why now
At this point, the system already knows how to store documents, parse them, assemble chunks, prefilter them, and normalize outputs. The LLM becomes a narrow extraction dependency instead of the center of the architecture.

### Required outputs
- LiteLLM adapter
- prompt builder
- response parser
- strict schema validation
- retry / repair policy
- caching key strategy
- model error mapping

### Stop/go criteria
Move on only if:
- gateway is fully mockable in tests
- prompt generation is deterministic for same inputs
- invalid JSON and retry paths are covered
- extraction output validates against the internal schema

---

## Phase 8 — Worker queue and run orchestration

### Implement
- `10_worker_queue_and_runs.md`
- `10_tests_worker_queue_and_runs.md`

### Goal
Connect the pipeline into an executable asynchronous run flow.

### Why after core modules
Workers should orchestrate existing stable modules, not contain business logic themselves.

### Required outputs
- job payload schema
- run state machine
- task handlers
- retry semantics
- step-level persistence updates
- orchestration services for parse → chunk → prefilter → extract → normalize → persist

### Stop/go criteria
Move on only if:
- a full run can execute end-to-end in tests with fakes
- retries do not duplicate persisted actions
- partial failures produce understandable run states
- jobs remain idempotent

---

## Phase 9 — End-to-end MVP hardening

### Implement
- `12_observability_resilience.md`
- `12_tests_observability_resilience.md`

### Goal
Add logs, metrics, tracing hooks, structured error handling, and operational safeguards.

### Why now
Observability is most useful once the main run flow exists. Before that, it is easy to over-engineer.

### Required outputs
- structured logs with run/document/chunk correlation IDs
- metrics around parse rate, prefilter rate, extraction attempts, failures
- timeout policy
- retry classification
- dead-letter or failure surfacing strategy

### Stop/go criteria
Move on only if:
- failures can be debugged from logs without stepping through code
- retryable vs non-retryable errors are separated
- run diagnostics are visible from API results or logs

---

## Phase 10 — Deployment and cloud MVP packaging

### Implement
- `13_deployment_and_cloud_mvp.md`
- `13_tests_deployment_and_cloud_mvp.md`

### Goal
Package the system for actual cloud execution.

### Why late
Deployment choices should package a working system, not compensate for unfinished module design.

### Required outputs
- Dockerfiles
- Compose or equivalent local stack
- environment contract
- migration startup plan
- worker startup plan
- secrets strategy
- health checks

### Stop/go criteria
MVP is cloud-ready only if:
- one command or one pipeline step boots the stack
- migrations run predictably
- API and worker can start independently
- cloud credentials are injectable via environment/secrets manager

---

## Phase 11 — Optional semantic indexing

### Implement only after the MVP works
- `11_qdrant_optional_indexing.md`
- `11_tests_qdrant_optional_indexing.md`

### Goal
Add vector search for later retrieval, deduplication, or exploration.

### Why last
It is not required to prove the main extraction MVP. Adding it earlier increases moving parts without helping the first successful pipeline run.

### Required outputs
- indexing adapter
- payload schema
- selective indexing policy
- sync/retry policy

### Stop/go criteria
Only proceed if:
- the base pipeline is already stable
- there is a concrete consumer for vector search
- indexing failures do not block the core run

---

## Recommended implementation rhythm per phase

For each phase, the coding agent should follow this exact loop:

1. Read the module spec.
2. Read the matching test spec.
3. Implement test fixtures/fakes first.
4. Write failing tests for the public contract.
5. Implement the minimal passing version.
6. Refactor only after tests pass.
7. Run the full test suite for that phase.
8. Only then move to the next phase.

---

## What should be mocked vs what should be real

### Prefer real in tests
- normalization logic
- chunk assembly logic
- repository logic against test Postgres or transactional DB fixture
- API routing and schema validation
- score calculation in prefilter

### Prefer fake, not mock
- object storage
- queue transport
- LLM gateway
- Docling adapter output when parser behavior itself is not under test

### Prefer mocks only at hard boundaries
- network clients
- cloud SDK failures
- timeout / retry boundaries
- cost-tracking / usage reporting hooks

The agent should avoid tests that mock internal functions of the same module. Those tests become brittle and do not validate behavior.

---

## Definition of “MVP complete”

The MVP is complete when the following path works reliably:

1. upload document
2. create run
3. worker parses document
4. worker assembles chunks
5. prefilter selects relevant chunks
6. LLM extracts action-centric records
7. outputs are normalized and persisted
8. API returns run status and extracted actions

Everything else is secondary.

---

## Anti-patterns to avoid during implementation

- building Qdrant before end-to-end extraction works
- adding generic abstraction layers with no active second implementation
- letting worker tasks contain parsing or extraction business rules inline
- coupling API schemas directly to ORM models
- storing only normalized outputs and losing raw extraction payloads
- using real cloud services in unit tests
- making LLM prompt construction depend on mutable global state
- writing tests that assert internal call counts instead of observable outcomes

---

## Final execution order summary

Implement in this order:

1. config and project layout
2. Postgres schema and repositories
3. object storage and ingest persistence
4. API service shell
5. Docling parse and chunk assembly
6. deterministic prefilter
7. normalization and identity
8. LLM gateway and extraction
9. worker queue and run orchestration
10. observability and resilience
11. deployment and cloud MVP packaging
12. optional Qdrant indexing

This is the recommended order for both code and test development.
