# Module: Configuration and Project Layout

## Goal

Establish a clean project skeleton, centralized settings loading, dependency wiring, and environment separation before any business logic is implemented.

## Recommended technologies

- Python 3.12+
- Pydantic v2
- `pydantic-settings` for configuration loading
- dependency injection by explicit constructors and FastAPI dependencies
- no hidden globals except a read-only cached settings factory

## Required package layout

```text
app/
  config/
    settings.py
    logging.py
  core/
    types.py
    errors.py
    constants.py
  domain/
  adapters/
  services/
  db/
  workers/
  api/
tests/
```

## Settings design

Create one root `Settings` object that nests smaller settings groups:

- `AppSettings`
- `ApiSettings`
- `PostgresSettings`
- `RedisSettings`
- `S3Settings`
- `DoclingSettings`
- `LiteLLMSettings`
- `PrefilterSettings`
- `WorkerSettings`
- `QdrantSettings` (optional / disabled by default)
- `ObservabilitySettings`

### Rules

1. All secrets must come from environment variables or mounted secret files.
2. No module should read environment variables directly.
3. Settings must be immutable after startup.
4. Boolean feature flags must be explicit:
   - `ENABLE_QDRANT`
   - `ENABLE_LLM_CACHE`
   - `ENABLE_PREFILTER_DEBUG_FIELDS`

## Initialization strategy

Implement a single settings factory:

- cache the loaded settings object,
- validate eagerly at process startup,
- fail fast on invalid configuration,
- expose settings through constructor injection, not module-level import chains.

## Dependency wiring

Do not build a service locator.

Instead:
- each service receives its collaborators via constructor parameters,
- FastAPI dependencies create request-scoped services only where needed,
- workers assemble their dependencies at startup.

## Shared interfaces to define early

- `ClockProtocol`
- `IdGeneratorProtocol`
- `ObjectStorageProtocol`
- `DocumentParserProtocol`
- `LLMClientProtocol`
- `VectorIndexProtocol`
- `RunRepositoryProtocol`
- `DocumentRepositoryProtocol`
- `ActionRepositoryProtocol`

This keeps tests stable while implementations evolve.

## Error model

Create base typed errors:

- `ConfigError`
- `DomainError`
- `ValidationError`
- `RetryableExternalError`
- `PermanentExternalError`
- `ParsingError`
- `ExtractionError`
- `NormalizationError`

External adapters must translate vendor/library exceptions into these internal error types.

## Logging baseline

Use structured logging with consistent fields:

- `event`
- `module`
- `document_id`
- `run_id`
- `chunk_id`
- `job_id`
- `attempt`
- `elapsed_ms`

No free-form print debugging in library code.

## Acceptance criteria

- project boots with one validated settings object,
- every external dependency is configured from settings,
- a new module can be added without circular imports,
- tests can override settings cheaply,
- no module reads `os.environ` directly outside config loading.

## Common failure modes to avoid

- implicit global clients,
- hidden environment access,
- settings objects mutated at runtime,
- config split across unrelated files,
- repository code importing API layer objects.
