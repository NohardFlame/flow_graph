# Testing Strategy: Optional Qdrant Indexing

## Test objective

Prove that the indexing adapter builds the correct payloads and upsert identities without requiring a real vector database for most tests.

## What to mock

Mock the Qdrant client boundary or use a fake vector index implementation.

## What not to mock

- payload construction
- deterministic point id generation
- failure-to-partial-success policy in orchestration logic

## Required tests

### Payload building
- payload includes all required filter fields
- optional fields are omitted or null per policy
- point id is deterministic

### Upsert behavior
- repeated upsert of same action/chunk overwrites or idempotently preserves according to policy
- batch indexing preserves order-independent correctness

### Failure handling
- adapter exceptions are translated to internal retryable/permanent errors
- orchestration layer records partial success if indexing is optional

### Config behavior
- module disabled means no index calls
- missing Qdrant config when disabled does not break startup

## Mocking guidance

Use a simple fake index with an in-memory dict keyed by point id. This lets tests assert final payload state naturally.

Reserve real Qdrant integration tests for a small optional suite.

## Anti-patterns

- requiring a live vector DB for unit tests,
- testing vector similarity itself in application tests,
- making adapter and orchestration tests depend on embedding generation.

## Success criteria

Indexing can be safely postponed or enabled later without destabilizing the core pipeline tests.
