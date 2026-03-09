# Testing Strategy: Normalization and Identity

## Test objective

Prove that canonical key generation is deterministic, alias rewriting works, and collisions are handled transparently.

## Test style

Pure unit tests with parametrized inputs are ideal here.

## What to mock

Almost nothing. This module should be deterministic and isolated.

## What not to mock

- normalization helpers
- transliteration rules
- alias tables
- collision logic

## Fixtures

- alias config fixture
- rewrite config fixture
- reserved-word config fixture
- sample extraction drafts with multilingual surface forms

## Required tests

### Basic normalization
- whitespace collapses
- punctuation normalization
- snake_case conversion
- transliteration / ASCII policy works as configured

### Alias handling
- known alias rewrites to canonical form
- unknown alias remains normalized surface form
- alias list preserves original terms

### Action key generation
- action key includes primary object
- missing object falls back per explicit policy
- same verb on different objects yields different keys

### Collision handling
- two surface forms collapsing to one key are recorded
- ambiguous mapping raises warning or unresolved flag
- reserved/bad output is rejected or repaired

### Determinism
- repeated runs with same inputs yield same output
- normalization version changes can intentionally change output

## Mocking guidance

Prefer table-driven tests with `pytest.mark.parametrize`.

If transliteration uses an external library, either:
- treat it as part of the deterministic implementation and test through it,
- or wrap it in a tiny adapter and test both wrapper and service.

## Anti-patterns

- snapshotting huge output blobs when a few canonical fields matter,
- hiding alias tables inside tests instead of using versioned fixture data,
- testing this module only through API or worker integration.

## Success criteria

This module should be one of the easiest to test exhaustively. High confidence here simplifies every later merge step.
