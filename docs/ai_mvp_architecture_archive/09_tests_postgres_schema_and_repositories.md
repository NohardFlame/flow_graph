# Testing Strategy: PostgreSQL Schema and Repositories

## Test objective

Prove that repositories enforce idempotency, transactions behave correctly, and schema-backed queries support the intended workflow.

## Test layers

### Unit tests
For pure query-building helpers or row/domain mapping functions.

### Repository integration tests
Against a real test PostgreSQL instance or close equivalent. This is one of the modules where real DB tests are worth it.

### Migration tests
Smoke-test Alembic upgrades on an empty database and, if feasible later, on a representative previous revision.

## What to mock

Very little at repository level.

## What not to mock

- SQLAlchemy session behavior
- repository methods
- transaction boundaries
- uniqueness/idempotency constraints

## Fixtures

- temporary test database
- session factory
- inserted document/run fixtures
- chunk/action factory helpers

## Required tests

### Basic persistence
- insert document and version
- create run
- persist chunks with feature payloads
- persist actions with evidence rows

### Idempotency
- repeated chunk insert with same `(run_id, chunk_hash)` does not duplicate
- repeated action persistence follows chosen policy
- rerun step can resume safely

### Transaction behavior
- failure mid-operation rolls back intended boundary
- partial persistence across steps is allowed only where explicitly designed

### Query correctness
- fetch run status with counts
- paginate actions for run
- fetch chunks by prefilter decision
- retrieve LLM call audit info

### Migration smoke tests
- apply all migrations to empty DB
- downgrade/upgrade if your policy supports it

## Mocking guidance

Do not replace PostgreSQL with broad mocks for repository tests.

If fast local Postgres is difficult in some environments, keep:
- pure mapping tests separate,
- heavier repository tests in an integration test group.

## Anti-patterns

- testing repositories only through API endpoints,
- asserting on raw SQL string text instead of outcomes,
- relying on SQLite as a perfect stand-in when using Postgres-specific features like `jsonb`.

## Success criteria

Repository and migration tests should catch the majority of persistence regressions before worker/API tests ever run.
