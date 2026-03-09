# Testing Strategy: Docling Parse and Chunking

## Test objective

Prove that parse conversion and chunk assembly preserve structure and create stable extraction windows, while keeping tests mostly independent of actual third-party parsing behavior.

## Testing split

### Adapter tests
Small number of tests that call the real Docling adapter on fixture documents.

### Service tests
Larger set of tests that operate on fake `ParsedDocument` / `SectionUnit` data without invoking Docling.

This split is essential: Docling is powerful but too heavy and version-sensitive to sit inside every unit test.

## What to mock

- Mock or fake the `DocumentParserProtocol` in chunk assembly service tests.
- Mock filesystem/temp-file behavior only at adapter boundaries when needed.

## What not to mock

- your chunk assembly algorithm
- serialization logic
- deterministic chunk id generation
- structural grouping rules

## Test fixtures

Prepare small document fixtures:
- simple markdown with headings,
- markdown with list of rules,
- simple table-heavy sample,
- malformed/unsupported document sample,
- multilingual sample if relevant.

Also prepare pure in-memory `SectionUnit` fixtures that mimic parser output.

## Required tests

### Adapter tests
- supported file converts successfully
- parse failure maps to internal error
- parse export contains expected top-level structure

### Chunk assembly tests
- heading and following paragraphs stay together
- table and nearby explanatory text stay together
- large section splits by subheading before token-only split
- overlap logic injects only intended context
- chunk ids are stable for identical inputs

### Serialization tests
- section path included
- lists preserved
- tables rendered in stable text form
- page furniture excluded

### Regression tests
Add golden tests for previously broken boundary cases:
- conditions separated from action,
- table rows split incorrectly,
- permissions block mixed with glossary text.

## Mocking guidance

The preferred fake parser should return a preconstructed `ParsedDocument`. This keeps unit tests deterministic and fast.

Do not assert on exact Docling private object shapes. Convert them into your own internal model first, then test against that model.

## Anti-patterns

- using real PDFs in every unit test,
- snapshotting entire Docling raw exports if the upstream library changes often,
- mixing parser adapter correctness with chunking policy correctness in one test.

## Success criteria

Chunking policy can evolve safely because its tests depend on your stable internal representation, not on Docling internals.
