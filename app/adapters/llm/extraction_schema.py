"""Versioned JSON Schema for extraction output. Used by the LLM adapter for response_format."""

EXTRACTION_SCHEMA_NAME = "action_draft_v1_1"
EXTRACTION_SCHEMA_VERSION = "1.1"

# JSON Schema for one action object: all properties optional, string or null.
_ACTION_ITEM_PROPERTIES = {
    "verb": {"type": "string"},
    "primary_object": {"type": "string"},
    "primary_actor": {"type": "string"},
    "input_state": {"type": "string"},
    "output_state": {"type": "string"},
    "action_label": {"type": "string"},
    "suggested_actor_canonical": {"type": "string"},
    "suggested_object_canonical": {"type": "string"},
    "suggested_verb_canonical": {"type": "string"},
    "suggested_state_canonical": {"type": "string"},
}

# Allow null per extraction contract: each value is string or null.
for _k in _ACTION_ITEM_PROPERTIES:
    _ACTION_ITEM_PROPERTIES[_k] = {"type": ["string", "null"]}

EXTRACTION_JSON_SCHEMA: dict = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": _ACTION_ITEM_PROPERTIES,
        "additionalProperties": False,
    },
}
