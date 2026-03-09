"""Parse and validate LLM extraction response into list of ExtractionDraft.

Strict schema: response must be a JSON array of action objects with allowed
string fields. Raises ValidationError on invalid JSON or schema violation.
"""

import json
from typing import Any

from app.core.errors import ValidationError
from app.domain.normalization_models import ExtractionDraft

# Allowed top-level keys for each action object (all optional per ExtractionDraft)
EXTRACTION_ACTION_KEYS = frozenset({
    "verb",
    "primary_object",
    "primary_actor",
    "input_state",
    "output_state",
    "action_label",
    "suggested_actor_canonical",
    "suggested_object_canonical",
    "suggested_verb_canonical",
    "suggested_state_canonical",
})


def parse_extraction_response(raw: str, schema_version: str) -> list[ExtractionDraft]:
    """Parse raw LLM response to JSON, validate structure, return list of ExtractionDraft.

    Args:
        raw: Raw string from model (expected JSON array of action objects).
        schema_version: Schema version for diagnostics (unused in MVP validation).

    Returns:
        List of ExtractionDraft; may be empty if model returned [].

    Raises:
        ValidationError: Invalid JSON or structure not matching extraction schema.
    """
    if not raw or not raw.strip():
        raise ValidationError("Extraction response is empty")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValidationError(f"Extraction response is not valid JSON: {e}") from e

    if not isinstance(data, list):
        raise ValidationError(
            f"Extraction response must be a JSON array, got {type(data).__name__}"
        )

    drafts: list[ExtractionDraft] = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValidationError(
                f"Extraction item at index {i} must be an object, got {type(item).__name__}"
            )
        # Only allow known keys; ignore extra keys or restrict to known set
        filtered: dict[str, Any] = {}
        for k, v in item.items():
            if not isinstance(k, str):
                raise ValidationError(
                    f"Extraction item at index {i}: keys must be strings, got key {k!r}"
                )
            if k not in EXTRACTION_ACTION_KEYS:
                raise ValidationError(
                    f"Extraction item at index {i}: unknown key {k!r}; allowed: {sorted(EXTRACTION_ACTION_KEYS)}"
                )
            if v is not None and not isinstance(v, str):
                raise ValidationError(
                    f"Extraction item at index {i}: value for {k!r} must be string or null, got {type(v).__name__}"
                )
            filtered[k] = v

        drafts.append(
            ExtractionDraft(
                verb=filtered.get("verb"),
                primary_object=filtered.get("primary_object"),
                primary_actor=filtered.get("primary_actor"),
                input_state=filtered.get("input_state"),
                output_state=filtered.get("output_state"),
                action_label=filtered.get("action_label"),
                suggested_actor_canonical=filtered.get("suggested_actor_canonical"),
                suggested_object_canonical=filtered.get("suggested_object_canonical"),
                suggested_verb_canonical=filtered.get("suggested_verb_canonical"),
                suggested_state_canonical=filtered.get("suggested_state_canonical"),
            )
        )

    return drafts
