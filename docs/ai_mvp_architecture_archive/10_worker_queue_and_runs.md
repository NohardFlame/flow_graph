# Module: Worker Queue and Run Orchestration

## Goal

Execute the document pipeline asynchronously, step by step, with resumability, bounded retries, and visible run state transitions.

## Recommended technologies

- ARQ worker
- Redis queue
- explicit run-step orchestration in service code

## Worker responsibilities

- dequeue jobs,
- load run context,
- execute pipeline steps,
- persist step transitions,
- retry retryable failures,
- mark permanent failures,
- emit events.

## Pipeline steps

Define explicit internal steps:
1. `ingest_ready`
2. `parse_document`
3. `build_chunks`
4. `prefilter_chunks`
5. `extract_actions`
6. `normalize_actions`
7. `persist_results`
8. `optional_index`
9. `complete_run`

Each step should be callable independently for debugging/resume purposes.

## Orchestration policy

Use a step runner pattern:

- read current run state,
- execute next step,
- persist step completion,
- continue until done or failed.

Avoid giant monolithic worker functions.

## Retry policy

### Retryable
- temporary object storage unavailability
- transient Docling/runtime issues only if known retryable
- provider timeout / rate limit
- transient DB connectivity issue

### Non-retryable
- invalid configuration
- unsupported file format
- deterministic normalization bug
- schema bug causing repeated invalid persistence

## Run state updates

Persist both:
- public run status (`queued`, `running`, `failed`, `succeeded`, `partial_success`)
- internal current step and step history

## Idempotency and resume

Each step must be safe to rerun.

Examples:
- parsing can overwrite the same artifact key for the same run,
- chunk persistence uses deterministic chunk hash,
- extraction writes are de-duplicated by chunk and extraction identity,
- normalization updates or inserts deterministically.

## Job payload design

Queue payload should be minimal:
- `run_id`
- maybe `document_id`
- maybe `attempt`

Do not serialize huge objects into Redis jobs.

## Timeouts and chunking of work

If a single document may generate many extraction chunks, consider splitting the extraction stage into sub-jobs later.

For MVP:
- one run job can process one document sequentially if expected volume is low.

## Acceptance criteria

- queue restarts do not corrupt run state,
- failed runs are inspectable,
- retryable failures can succeed on retry,
- a worker crash does not require manual DB cleanup for normal cases.

## Common pitfalls

- hiding step transitions inside logs only,
- one huge try/except around the full pipeline,
- non-idempotent inserts,
- storing giant artifacts inside the queue payload.
