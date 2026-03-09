# Testing Strategy: Observability and Resilience

## Test objective

Prove that logs/events/metrics hooks fire at the right boundaries and that error classification drives expected behavior.

## What to mock

- log sink or metric emitter adapters if they are external
- external error sources via fake collaborators

## What not to mock

- your error classification logic
- event construction
- retryability decisions
- correlation id propagation helpers

## Required tests

### Error classification
- known provider timeout -> retryable external
- unsupported file format -> permanent external
- unexpected bug -> internal error class

### Event emission
- step started/completed emitted around successful step
- step failed emitted on failure
- retry event emitted on retry path
- partial success event emitted when optional indexing fails

### Logging
- structured log record contains expected keys
- correlation id is propagated from API to worker context if designed that way

### Metrics
- counters increment on run success/failure
- prefilter counters reflect accept/gray/reject results
- cache hit metric increments on cached LLM responses

## Mocking guidance

Use simple in-memory collectors for:
- logs,
- metrics,
- emitted events.

These are more robust than patching logger internals line by line.

## Anti-patterns

- asserting exact human log messages,
- depending on production monitoring backends in unit tests,
- testing metrics only indirectly via dashboards.

## Success criteria

A regression in retryability or event emission should fail fast in tests before it reaches staging.
