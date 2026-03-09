# Testing Strategy: Deployment and Cloud MVP

## Test objective

Prove that the packaged system starts correctly, validates configuration, and supports a basic end-to-end processing flow in a production-like environment.

## Test layers

### Container smoke tests
- API process starts
- worker process starts
- migrations apply
- health endpoints respond

### Environment validation tests
- missing critical env vars fail fast
- disabled optional modules do not require their configs

### End-to-end smoke test
In a controlled environment:
- upload sample document
- create run
- observe completion
- fetch resulting actions

## What to mock

For deployment smoke tests, avoid mocks where possible.
For CI speed, you may stub the LLM adapter with a fake service.

## What not to mock

- process startup
- container entrypoints
- migration execution
- settings loading

## Required tests

### Startup
- API exits non-zero on invalid config
- worker exits non-zero on invalid config
- readiness endpoint reports unavailable dependency when critical service is down

### End-to-end
- system processes one sample file successfully with fake LLM
- artifacts and DB rows are created as expected
- rerun of same document follows chosen versioning/idempotency policy

### Optional feature toggles
- Qdrant disabled path works
- audit/debug artifact mode works when enabled

## Mocking guidance

For CI, use:
- fake LLM service or fake adapter,
- local object storage compatible service or in-memory substitute depending on test depth.

Keep at least one realistic end-to-end smoke test, even if all expensive dependencies are faked.

## Anti-patterns

- requiring a real commercial LLM in CI,
- no startup validation tests,
- only unit-testing modules without one integrated pipeline smoke test.

## Success criteria

A new coding agent should be able to deploy the stack to staging and immediately know whether the full path is alive from these tests.
