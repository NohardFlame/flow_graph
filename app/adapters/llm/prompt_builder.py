"""Build extraction prompts from chunk and config. Pure, versioned, deterministic."""

from __future__ import annotations

from app.domain.parse_models import ExtractionChunk

# JSON schema description for the model (matches EXTRACTION_ACTION_KEYS in response_parser)
EXTRACTION_JSON_SCHEMA_DESCRIPTION = """Respond with a single JSON array of action objects. Each object may have these string fields (all optional): verb, primary_object, primary_actor, input_state, output_state, action_label, suggested_actor_canonical, suggested_object_canonical, suggested_verb_canonical, suggested_state_canonical. Use null for missing values. Example: [{"verb": "submit", "primary_object": "form", "primary_actor": "user"}]"""


def build_extraction_messages(
    chunk: ExtractionChunk,
    prompt_version: str,
    schema_version: str,
    normalization_hint: str | None = None,
) -> list[dict[str, str]]:
    """Build system + user messages for extraction. Deterministic for same inputs.

    Args:
        chunk: The extraction window (chunk_id, section_path, chunk_text, etc.).
        prompt_version: Prompt version identifier (included in message for audit).
        schema_version: Schema version identifier (included in message for audit).
        normalization_hint: Optional short guidance for canonical forms.

    Returns:
        List of message dicts with "role" and "content" for chat completion.
    """
    section_path_str = " > ".join(chunk.section_path) if chunk.section_path else "(root)"
    chunk_meta = (
        f"Chunk ID: {chunk.chunk_id}\n"
        f"Section path: {section_path_str}\n"
        f"Estimated tokens: {chunk.estimated_tokens}"
    )
    evidence_instruction = (
        "Extract only action-centric facts that are clearly supported by the chunk text. "
        "Do not infer actions not stated or implied in the text. "
        "Include verb, primary actor, primary object, and state transitions where present."
    )
    norm_guidance = (
        normalization_hint
        if normalization_hint
        else "Use short, consistent labels. Suggested canonical fields are for downstream normalization."
    )
    system_content = (
        f"You are an extraction assistant. Output schema version: {schema_version}. "
        f"Prompt version: {prompt_version}.\n\n"
        f"{EXTRACTION_JSON_SCHEMA_DESCRIPTION}\n\n"
        f"Normalization: {norm_guidance}\n\n"
        f"Evidence: {evidence_instruction}"
    )
    user_content = (
        f"{chunk_meta}\n\n---\n\nChunk text:\n\n{chunk.chunk_text}"
    )
    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]
