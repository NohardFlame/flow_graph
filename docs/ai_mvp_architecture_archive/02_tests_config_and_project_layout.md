# Testing Strategy: Configuration and Project Layout

## Test objective

Prove that configuration loading is deterministic, validated, override-friendly, and isolated from business modules.

## Test philosophy

Most tests here are pure unit tests. Do not mock Pydantic itself. Test your own settings wrappers and factories.

## What to mock

- Only environment access boundaries when needed.
- Use `pytest` `monkeypatch` for environment variables and import-time overrides.

## What not to mock

- Do not mock `BaseSettings` behavior.
- Do not mock your own dataclasses or settings models.
- Do not mock logging configuration internals unless absolutely necessary.

## Fixture design

Create reusable fixtures:

- `env_minimal_valid`
- `env_missing_required_var`
- `env_invalid_port`
- `settings_factory_uncached`

Use `monkeypatch.setenv` and `monkeypatch.delenv` rather than patching internal helper functions.

## Required tests

### Settings loading
- loads valid settings from environment
- applies defaults when optional values are omitted
- raises on missing required values
- raises on invalid types
- respects feature flags

### Caching
- repeated factory calls return the same object when caching is enabled
- cache reset in tests creates a fresh object

### Dependency boundaries
- modules do not read `os.environ` directly
- constructing services without required dependencies fails fast

### Error translation
- invalid settings map to your internal `ConfigError` if you wrap them

## Mocking guidance

Use monkeypatch at the boundary:
- patch `os.environ`,
- patch secret-file path readers if implemented,
- avoid patching nested helpers unless they hit the network or filesystem.

## Anti-patterns

- asserting exact internal Pydantic error text,
- sharing mutated settings objects across tests,
- importing app modules before env setup if those modules read config at import time.

## Coverage target

High branch coverage. This module is small and foundational; it should be close to exhaustive.
