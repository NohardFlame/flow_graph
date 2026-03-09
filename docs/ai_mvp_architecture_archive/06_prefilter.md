# Module: Deterministic Prefilter

## Goal

Score extraction chunks using cheap deterministic and classical IR signals, so only promising chunks are sent to the expensive model.

## Architectural position

This module is the main token-saving control point. It must be understandable, debuggable, and cheap.

It is **not** just a keyword list.

## Prefilter design: scoring cascade

Implement a cascade that combines multiple feature groups.

### Feature group A: structural features
Signals derived from chunk metadata:
- heading path contains process/status/role/permission terms
- chunk contains a list or table
- chunk belongs to appendix/glossary/introduction section
- chunk depth in document hierarchy
- chunk proximity to previously relevant chunk in same section

### Feature group B: exact and alias matches
Use fast exact matching for normalized phrases:
- actor lexicon
- action verb lexicon
- permission/restriction lexicon
- state lexicon
- condition lexicon

Back this with a multi-pattern matcher.

### Feature group C: token-pattern matches
Use token-level patterns for constructions such as:
- role + modal verb + action
- object + state transition phrase
- if/when condition + action
- prohibition pattern
- automatic system action pattern

### Feature group D: context boosts
Boost when multiple signal types co-occur near each other:
- action term near object term
- modal/restriction term near role term
- state term near object term

### Feature group E: lexical relevance score
Use TF-IDF or BM25-like scoring against a small set of seeded queries:
- user action
- system action
- state transition
- permission
- restriction
- validation rule

## Recommended MVP stack

- exact phrase matching via a fast multi-pattern matcher
- token pattern matching via spaCy matcher abstractions
- TF-IDF lexical score in-process
- no LLM in this stage
- no heavy dependency parsing in the hot path

## Module outputs

For each chunk produce:

- `prefilter_score`
- `decision` (`accept`, `gray`, `reject`)
- `feature_breakdown`
- `matched_terms`
- `matched_patterns`
- `structural_flags`
- `lexical_score`

Persisting this metadata is strongly recommended for debugging and threshold tuning.

## Thresholding strategy

Use three bands:

### Accept
Send directly to extraction.

### Gray
Send a small configurable proportion:
- top-N gray chunks per document,
- or chunks adjacent to accepted chunks.

### Reject
Do not send to extraction.

This preserves recall better than a hard binary cut.

## Configuration

Expose weights and thresholds in config:
- structural weights
- exact match weights
- pattern weights
- context boosts
- lexical score weight
- accept threshold
- gray threshold
- top gray budget per document

## Lexicon management

Store lexicons and pattern config as versioned data files, not hard-coded scattered constants.

Suggested categories:
- action verbs
- permission terms
- restriction terms
- role nouns
- state indicators
- transition indicators
- condition indicators
- object domain terms

## Engineering rules

1. Feature extraction must be deterministic.
2. Score calculation must be reproducible.
3. Feature breakdown must be inspectable.
4. Threshold tuning must not require code changes where possible.
5. Missing spaCy model or lexical resources must fail fast at startup.

## Acceptance criteria

- module reduces chunk count materially before LLM stage,
- false negatives are constrained by gray-zone policy,
- score breakdown explains why a chunk was accepted or rejected,
- scoring config can be tuned without changing algorithm code.

## Common pitfalls

- giant unstructured keyword list,
- hidden magic thresholds,
- no persisted explanation for why a chunk was filtered,
- using only structural signals or only lexical signals,
- pushing every uncertain chunk to the LLM anyway.
