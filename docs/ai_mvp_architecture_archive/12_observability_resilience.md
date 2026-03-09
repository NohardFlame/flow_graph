# Module: Observability and Resilience

## Goal

Make the MVP debuggable in production and robust against common external failures without burying logic under excessive infrastructure.

## Scope

This module owns:
- structured logging conventions,
- error taxonomy,
- retry classification,
- run event emission,
- latency/cost counters,
- minimal health/readiness checks,
- debug artifact retention policy.

## Logging strategy

Use structured logs with consistent keys:
- `event`
- `module`
- `document_id`
- `run_id`
- `chunk_id`
- `job_id`
- `step`
- `attempt`
- `provider`
- `model`
- `elapsed_ms`

Log at boundaries:
- upload accepted
- storage write complete
- parse start/end
- chunking complete
- prefilter decision summary
- extraction call start/end
- normalization complete
- run success/failure

## Metrics to capture

At minimum:
- documents uploaded
- runs started/succeeded/failed/partial
- average chunks per run
- chunks accepted/gray/rejected by prefilter
- LLM calls count
- cache hit rate
- token usage
- estimated LLM spend
- step latency
- parse failures
- extraction validation failures

## Error classification

Every caught external exception must become one of:
- retryable external
- permanent external
- internal bug / unexpected

This drives retry policy and alerting.

## Run events

Persist meaningful step events in DB:
- step started
- step completed
- step retried
- step failed
- run completed
- run marked partial success

These events are more reliable for debugging than logs alone.

## Health endpoints

### Liveness
Simple process-alive check.

### Readiness
Check critical dependencies only at shallow depth:
- DB reachable
- Redis reachable if worker/API requires it
- object storage auth optionally shallow-checked

Do not turn readiness into a long expensive dependency probe.

## Debug policy

Debug artifacts should be configurable:
- disabled in cheapest mode,
- enabled in staging and targeted production investigations.

## Acceptance criteria

- a failed run can be investigated from logs + DB events + stored artifacts,
- retry behavior is explainable,
- token usage and cache hits are visible,
- correlation ids tie API, worker, and LLM events together.

## Common pitfalls

- free-form logs with no stable fields,
- no distinction between retryable and permanent errors,
- zero visibility into why prefilter rejected chunks,
- no persistent step history,
- overloading readiness checks with deep integration behavior.
