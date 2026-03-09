# Module: LLM Gateway and Extraction

## Goal

Build prompts, invoke the model through a single adapter layer, validate output, and keep model usage observable, cacheable, and replaceable.

## Recommended technologies

- LiteLLM SDK or Proxy as the single LLM integration surface
- JSON-schema-oriented extraction contract
- Pydantic validation of outputs
- low-temperature extraction calls
- optional repair pass only for invalid JSON

## Scope

This module owns:
- prompt rendering,
- model selection,
- request metadata,
- retries for retryable failures,
- output validation,
- optional repair path,
- capture of usage and cost metadata.

It does **not** own normalization or repository persistence.

## Extraction design

The extractor consumes:
- `ExtractionChunk`
- prompt template version
- extraction schema version

The extractor returns:
- validated `ActionRecordDraft` list
- raw model metadata
- token/cost metadata
- any warnings

## Prompt construction rules

Prompt must include:
- system instructions,
- chunk metadata,
- normalization guidance,
- strict JSON schema,
- evidence discipline.

Prompt builder should be pure and versioned:
- `prompt_name`
- `prompt_version`
- `schema_version`

Persist these versions with every extraction result.

## Model routing policy

For MVP define one primary extraction model and one fallback model.

Fallback is used only for:
- rate-limit failure,
- transient provider failure,
- context window mismatch if explicitly configured.

Do not silently switch models without recording it.

## Caching policy

Enable request caching keyed by:
- model identifier,
- prompt version,
- schema version,
- chunk hash,
- normalization config version.

A cache hit must bypass model invocation but still emit normal observability events.

## Retry policy

Retry only retryable errors:
- timeouts,
- 429/rate limit,
- transient upstream failures.

Do not retry:
- schema invalid due to clearly bad prompt design more than once,
- permanent auth/config errors,
- deterministic content-policy refusals if relevant.

## Repair policy

Only perform a repair call if:
- response is not valid JSON or fails schema parsing,
- a short repair prompt is cheaper than re-extraction,
- repair attempts are capped.

Store both original invalid output and repaired output when audit mode is enabled.

## Usage accounting

Persist per extraction call:
- provider/model,
- input tokens,
- output tokens,
- estimated cost if available,
- cache hit/miss,
- latency,
- retry count.

## Adapter contract

Define `LLMClientProtocol` with methods like:
- `extract_actions(chunk, prompt_cfg) -> ExtractionResult`
- `repair_json(raw_output, schema_cfg) -> RepairResult`

Wrap provider exceptions immediately.

## Acceptance criteria

- switching provider/model requires no changes outside adapter/config,
- extraction results are schema-validated before leaving the module,
- cache hits are visible,
- retries are bounded and predictable,
- prompt/schema versions are persisted for reproducibility.

## Common pitfalls

- letting service code call LiteLLM directly,
- mixing prompt rendering with repository writes,
- hiding fallback model switches,
- retrying invalid prompts forever,
- not storing model metadata for debugging.
