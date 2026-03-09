# Testing Strategy: LLM Gateway and Extraction

## Test objective

Prove that prompt rendering, adapter behavior, validation, retry logic, cache behavior, and repair flow work without depending on live model calls in normal test runs.

## Preferred doubles

### Fake LLM adapter
Return controlled responses:
- valid extraction JSON,
- invalid JSON,
- transient error,
- permanent error,
- cache hit metadata.

### Spy prompt renderer
Useful if prompt versioning/rendering must be verified.

## What to mock

- network/provider boundary only
- LiteLLM adapter calls in service-level tests

## What not to mock

- prompt builder
- schema validator
- retry policy
- repair decision policy
- extraction result parsing

## Required tests

### Prompt rendering
- includes chunk metadata
- includes schema version
- includes evidence instructions
- deterministic output for same inputs

### Success path
- valid LLM JSON parses into action draft models
- token/cost metadata is captured
- model id and versions are attached

### Retry path
- transient failure retries up to configured cap
- permanent failure stops immediately
- fallback model use is recorded if enabled

### Repair path
- invalid JSON triggers repair once
- repaired JSON returns parsed result
- repeated invalid responses fail cleanly with stored diagnostics

### Cache path
- identical request uses cached response
- cache hit flag is exposed
- cache key includes prompt/schema/model versions

## Mocking guidance

The fake LLM adapter should be stateful enough to simulate:
- first call timeout, second call success,
- invalid initial response then valid repair response.

Avoid brittle mocks that assert exact prompt strings line-by-line unless prompt contract itself is the subject of the test.

## Anti-patterns

- live LLM calls in unit tests,
- relying on vendor-specific raw response shape in domain tests,
- asserting exact token counts from fake data unless deliberately specified.

## Success criteria

A provider swap or prompt text refactor should only require small updates in adapter or prompt tests, not in every extraction service test.
