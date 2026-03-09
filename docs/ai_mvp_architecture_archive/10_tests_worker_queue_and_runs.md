# Testing Strategy: Worker Queue and Run Orchestration

## Test objective

Prove that step progression, retries, idempotency, and failure handling work correctly with minimal dependence on a live Redis queue in most tests.

## Test split

### Pure orchestration tests
Call the run-step service directly with fake collaborators.

### Queue integration smoke tests
Small set of tests that verify ARQ job wiring if desired.

## What to mock

Mock or fake the step services:
- parser
- chunk builder
- prefilter
- extractor
- normalizer
- repositories
- optional vector index

## What not to mock

- step transition logic
- retry decision logic
- run status mapping
- event emission logic within your service

## Preferred fakes

Create stateful fakes that can simulate:
- first attempt failure, second attempt success
- partial prior progress before resume
- idempotent repeated inserts

## Required tests

### Happy path
- all steps execute in order
- run ends in succeeded state
- events recorded for each step

### Retryable failure
- transient step error causes retry behavior
- run remains resumable
- retry count is recorded

### Permanent failure
- non-retryable step error marks run failed
- downstream steps are not executed
- error code/message recorded

### Resume behavior
- run resumes from next incomplete step
- already persisted chunks/actions are not duplicated

### Idempotency
- rerunning whole job after partial success does not double-write

## Mocking guidance

Prefer fakes over mocks for collaborators with state transitions. This lets you assert final repository state and emitted events rather than fragile call order alone.

If using ARQ integration tests:
- keep them few,
- isolate them behind markers,
- assert that job payloads are minimal and correctly interpreted.

## Anti-patterns

- relying on a real Redis queue for all orchestration tests,
- testing only the queue wrapper and not the run-step logic,
- collapsing all failure paths into one generic exception test.

## Success criteria

The orchestration layer should be well covered even if Redis is unavailable in local fast test runs.
