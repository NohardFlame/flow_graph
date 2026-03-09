# Testing Strategy: Object Storage and Ingest

## Test objective

Prove that object storage keying, checksum logic, and error handling are correct without depending on real cloud infrastructure in most tests.

## Preferred test doubles

### Primary fake
Create an in-memory fake object storage adapter that mimics:
- put,
- get,
- head,
- download,
- metadata access.

This fake should store:
- bytes,
- content type,
- size,
- checksum or metadata.

### Secondary integration option
Add a small set of optional integration tests against local S3-compatible storage if needed later.

## What to mock

Mock only the low-level vendor client in adapter unit tests if you want to test exception mapping.

## What not to mock

- key generation logic
- checksum calculation
- your storage adapter public methods
- your ingest service orchestration logic

## Required tests

### Keying
- source key generation is deterministic
- parse artifact keys include run id
- user-supplied filename cannot escape prefix structure

### Upload
- stores bytes and metadata
- computes checksum correctly
- records size correctly
- supports stream and bytes upload paths

### Download
- retrieves expected bytes
- writes temp file and cleans up per policy
- raises internal not-found error for missing object

### Error mapping
- vendor timeout/network errors become retryable internal errors
- permanent errors map to permanent internal errors

### Idempotency/retry
- repeated `put` with same key follows the chosen policy
- ingest service does not enqueue processing if storage upload fails

## Mocking guidance

For service-level tests:
- use the fake object store,
- use a fake repository and fake queue,
- assert resulting state, not only method calls.

For adapter-level tests:
- patch the vendor client method that throws,
- assert translated error type.

## Anti-patterns

- overusing Moto-like heavy test infrastructure for every unit test,
- asserting raw SDK exceptions in service tests,
- hiding key generation inside tests instead of using the real function.

## Success criteria

Most tests run entirely offline and still give confidence that a later S3/MinIO swap will not break the service contract.
