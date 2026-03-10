# JSON Schema Migration and Prompt-Contract Alignment

## Goal

Make LLM extraction more reliable by moving the output schema out of the prompt text and into the model call configuration, while keeping the current pipeline stable.

This note supplements:
- `07_llm_gateway_and_extraction.md`
- `07_tests_llm_gateway_and_extraction.md`
- `08_normalization_and_identity.md`
- `00_MASTER_IMPLEMENTATION_ORDER.md`

## Decision summary

Use a **two-part extraction contract**:

1. **JSON Schema in the LLM request configuration**
   - the provider or LiteLLM adapter enforces shape,
   - the prompt describes extraction semantics only.

2. **Prompt stays action-centric but remains constrained to the current schema version**
   - do **not** add new output fields in this migration,
   - do **not** break the current response parser or downstream normalizer.

This migration is intentionally **non-breaking**.

## Why this change

The current prompt mixes two concerns:
- what the model should extract,
- what JSON shape it must return.

That makes the prompt longer, weaker semantically, and harder to maintain.

Moving schema enforcement into `response_format` / JSON Schema improves:
- output reliability,
- prompt clarity,
- testability,
- provider portability inside the adapter layer.

## Contract alignment assessment

## What already aligns well

The proposed new prompt is consistent with the architecture in these ways:
- it keeps **action-centric extraction** as the primary unit;
- it preserves **deterministic downstream normalization** by keeping `suggested_*_canonical` fields as hints rather than truth;
- it fits the existing `LLM Gateway and Extraction` module boundary, where prompt construction and schema validation live together;
- it supports the existing retry/cache/versioning model.

## What does **not** fully align yet

The earlier architecture overview describes a richer `ActionRecord` shape with items such as:
- conditions,
- permissions,
- restrictions,
- evidence references,
- possibly multiple actors/objects.

The **current extraction contract in code does not expose those fields**. It only supports a minimal single-action draft with:
- `verb`
- `primary_object`
- `primary_actor`
- `input_state`
- `output_state`
- `action_label`
- `suggested_*_canonical`

Because of that, the new prompt must be integrated in a **contract-aware** way:
- it may mention permissions/prohibitions and state transitions as things to interpret,
- but it must still map them back into the current minimal field set,
- and it must **not** ask the model to emit fields the parser cannot accept.

## Integration decision

For this migration, treat the current extractor output as **`ActionDraft v1.1`**, not as the full future `ActionRecord`.

That means:
- the prompt should improve semantic guidance,
- the schema should move into the request configuration,
- but the payload shape stays the same.

Do **not** attempt a richer extraction schema in the same change.

If richer action semantics are still desired later, introduce a separate **schema v2** as a versioned follow-up migration.

## Implementation plan

## Step 1 — Define a real JSON Schema object in code

Create a versioned schema object in the extraction module, for example:
- `EXTRACTION_SCHEMA_NAME = "action_draft_v1_1"`
- `EXTRACTION_SCHEMA_VERSION = "1.1"`
- `EXTRACTION_JSON_SCHEMA = {...}`

Schema requirements:
- top-level type: `array`
- items: `object`
- allowed properties only: current parser keys
- each value type: `string` or `null`
- `additionalProperties: false`

Keep the schema in code near the response parser / extraction adapter, not inside prompt text.

## Step 2 — Simplify the prompt builder

Refactor the prompt builder so that it no longer contains a prose description of the JSON format.

The prompt should now focus on:
- what counts as an action,
- how to split one chunk into multiple action objects,
- when to use `null`,
- how conservative canonical suggestions should be,
- short examples that match the existing fields.

Keep the prompt deterministic and versioned.

## Step 3 — Update the LiteLLM adapter

In the LLM adapter, pass the schema through the structured-output mechanism supported by the selected provider.

Adapter requirements:
- accept `schema_name`, `schema_version`, and the concrete JSON Schema object;
- pass them through `response_format` or provider-equivalent structured-output config;
- store provider/model metadata exactly as before;
- expose whether structured schema enforcement was used.

If the chosen provider does not support structured outputs for that model, the adapter must:
- record this explicitly,
- fall back to JSON-mode or text mode only if configured,
- still validate locally with Pydantic / parser logic.

This fallback must be visible in logs and metadata.

## Step 4 — Keep parser and normalizer contracts unchanged

Do not change downstream contracts in this migration.

The response parser should still parse the same minimal fields.
The normalizer should still compute canonical keys from:
- surface fields,
- model-suggested canonical hints,
- deterministic code rules.

This preserves compatibility with:
- repository writes,
- normalization logic,
- run metadata,
- cached responses keyed by schema version.

## Step 5 — Make versioning explicit

Persist all of the following with each extraction call:
- prompt name/version,
- schema name/version,
- model id,
- whether structured schema mode was enabled,
- whether fallback mode was used.

This is required for auditability and reproducibility.

## Step 6 — Defer richer schema changes

Do not add fields such as:
- `permissions`
- `restrictions`
- `conditions`
- `evidence`
- arrays of actors/objects

inside this migration.

If those are needed, create a separate `ActionDraft v2` plan with:
- response parser changes,
- normalizer changes,
- repository/storage changes,
- migration of cache keys and test fixtures.

## Prompt integration guidance

When integrating the improved prompt, keep these constraints:

1. **Action-centric semantics are good and should stay.**
   The new prompt is better than the current one because it defines what counts as an extractable action.

2. **Examples must stay minimal and field-compatible.**
   Only include examples that use the current allowed keys.

3. **Do not promise evidence fields in the prompt.**
   The architecture mentions evidence discipline, but the current extraction contract does not return evidence objects. For now, grounding comes from chunk provenance already present in parsing/chunk metadata.

4. **Do not overclaim permission/restriction support.**
   The prompt may instruct the model to interpret prohibitions or permissions into the minimal schema, but not to output dedicated permission fields.

5. **Canonical suggestions remain hints.**
   Final identity is still computed by the normalization module in code.

## Testing impact

Update `07_tests_llm_gateway_and_extraction.md` coverage with these additional checks:

### Prompt tests
- prompt no longer embeds a long prose JSON schema description;
- prompt still includes prompt version and schema version metadata;
- prompt examples only use supported keys.

### Adapter tests
- structured-output config is passed to the provider adapter;
- unsupported-provider fallback is explicit and observable;
- schema version participates in cache keys.

### Parser tests
- valid structured output parses identically to the previous contract;
- extra fields are rejected;
- `null` handling remains stable.

### Integration tests
- one end-to-end extraction run succeeds with structured schema mode enabled;
- the same run remains reproducible from stored prompt/schema versions.

## Recommended rollout

Use this rollout order:

1. add JSON Schema object and tests;
2. update adapter to pass structured-output config;
3. simplify prompt builder;
4. switch extraction calls to the new prompt version;
5. monitor invalid-output rate and fallback usage;
6. only then consider a richer schema v2.

## Recommended final state after this migration

After this change, the extraction module should behave like this:
- **prompt** = semantic instructions only,
- **JSON Schema** = output contract enforced at request level,
- **parser** = local validation and typed conversion,
- **normalizer** = final canonical identity in code,
- **repositories** = unchanged.

That is the cleanest fit with the architecture already defined in the archive.
