# Testing Strategy: Deterministic Prefilter

## Test objective

Prove that feature extraction, score aggregation, thresholds, and explainability work correctly and remain stable as lexicons evolve.

## Preferred test style

Mostly pure unit tests over in-memory chunk fixtures.

## What to mock

- Mock NLP model loading only in startup/config tests.
- Fake lexical scorer if you want to isolate score combiner tests.

## What not to mock

- feature calculators
- weight application
- threshold logic
- explanation payload generation

## Test fixtures

Create a corpus of tiny chunk fixtures labeled by intent:
- explicit action
- permission
- restriction
- state transition
- glossary noise
- intro/overview noise
- edge case gray chunk
- table-based rule chunk
- false-positive trap chunk

Each fixture should include:
- text,
- section path,
- structural flags,
- expected notable features.

## Required tests

### Feature extraction
- exact term matches are found after normalization
- pattern matches fire on expected constructions
- structural boosts apply from heading path
- appendix/glossary penalties apply
- context boosts require intended co-occurrence

### Scoring
- weights combine deterministically
- turning off a feature family changes score as expected
- accept/gray/reject thresholds behave correctly

### Explainability
- feature breakdown contains all contributing signals
- rejected chunks still include enough diagnostics for tuning

### Gray-zone policy
- top-N gray chunks selected correctly
- adjacent-to-accepted policy works if enabled

### Regression tests
Record past misses and false positives as fixtures.

## Mocking guidance

Keep most tests independent of spaCy internals:
- either test pattern functions on tokenized fixtures,
- or wrap spaCy matcher calls in a small adapter and test the adapter separately.

For lexical score tests:
- use fixed mini corpora to avoid drift,
- assert relative ordering instead of exact floating-point values unless normalized.

## Anti-patterns

- requiring full parser output in every prefilter test,
- depending on external NLP downloads in CI,
- asserting on all score decimals when only rank/order matters.

## Coverage target

Very high. This module is one of the most important cost-control points in the system.
