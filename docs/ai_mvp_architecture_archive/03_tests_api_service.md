# Testing Strategy: API Service

## Test objective

Prove that the API validates input, coordinates collaborators correctly, and returns stable contracts without performing heavy work inline.

## Test layers

### Unit tests
Test handler behavior against mocked service interfaces.

### API contract tests
Use FastAPI `TestClient` or async client to verify routes, payload schemas, and status codes.

### Lightweight integration tests
Use temporary database and fake object storage adapter for end-to-end upload flow without real cloud dependencies.

## What to mock

Mock at service boundaries:
- document service
- run service
- queue enqueue adapter
- object storage adapter

Prefer fakes over mocks where stateful behavior matters.

## What not to mock

- request/response validation
- routing
- Pydantic response serialization
- your own API schemas

## Fixture plan

- `api_client`
- `fake_object_storage`
- `fake_queue`
- `db_session`
- `sample_multipart_file`
- `correlation_id_headers`

## Required tests

### Upload route
- accepts valid document
- rejects unsupported extension
- rejects oversize file
- persists metadata before enqueue
- handles object storage failure
- handles queue failure after storage write according to policy

### Run creation
- creates run for existing document
- rejects unknown document id
- prevents invalid duplicate active run if policy forbids it

### Read endpoints
- return 404 for unknown ids
- paginate chunk/action lists
- map internal statuses to public enum

### Error handling
- internal exceptions become structured error responses
- correlation id is present in responses / logs if designed that way

## Mocking guidance

Use spies or call-recording fakes rather than asserting fragile call counts unless call counts matter for idempotency.

For upload tests:
- fake object storage should store bytes in memory and expose inspection methods.
- fake queue should store enqueued payloads in a list.

## Anti-patterns

- snapshot testing entire responses with volatile timestamps,
- mocking FastAPI internals,
- testing both API logic and repository logic in the same unit test.

## Success criteria

A coding agent should be able to change repository internals without breaking API tests unless the external HTTP contract changes.
