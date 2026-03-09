# Module: Normalization and Identity

## Goal

Transform extracted draft values into deterministic canonical keys for actors, objects, actions, and states so later merge logic is simple, stable, and auditable.

## Core principle

LLM output may suggest canonical names, but final canonical identity is computed in code.

## Responsibilities

This module owns:
- string normalization,
- transliteration or controlled English slug generation,
- alias collapse within a run,
- deterministic key derivation,
- collision policy,
- primary entity selection when multiple candidates exist.

It does not own full semantic dedup across all documents beyond deterministic rules.

## Canonical key policy

### Actor key
`<normalized_role_name>`

### Object key
`<normalized_object_name>`

### Action key
`<normalized_verb>_<primary_object_key>`

### State key
`<object_key>__<normalized_state_name>` or equivalent stable format

## Normalization pipeline

For each name-like field:

1. trim and normalize whitespace
2. lowercase
3. normalize punctuation and separators
4. transliterate or map to controlled ASCII/English form if required
5. remove low-information stop words where policy allows
6. convert to snake_case slug
7. apply alias dictionary rewrite
8. validate against reserved words / empties

## Aliases and rewrite tables

Keep versioned config files for:
- role aliases
- object aliases
- action verb rewrites
- state rewrites
- banned ambiguous forms

These rewrites must be explicit and reviewable.

## Collision policy

When two different surface forms map to the same canonical key:
- keep both source forms as aliases,
- record collision event,
- allow merge only if allowed by configured rule set.

When one surface form could map to multiple keys:
- prefer deterministic local rule,
- otherwise keep the candidate unresolved and mark warning.

## Output model

Produce a normalized action record that includes:
- original surface forms,
- model-suggested canonical forms,
- final computed canonical keys,
- alias list,
- warnings,
- normalization version.

## Determinism requirement

Given the same raw extracted draft and the same normalization config version, output must be identical.

## Acceptance criteria

- canonical keys are stable across reruns,
- action keys include primary object identity,
- collisions are observable rather than silently swallowed,
- normalization behavior can be tuned by config data rather than code edits alone.

## Common pitfalls

- trusting LLM canonical fields as final truth,
- deriving action key from verb alone,
- silently collapsing distinct roles,
- making normalization language-specific in scattered helper code,
- losing original surface forms.
