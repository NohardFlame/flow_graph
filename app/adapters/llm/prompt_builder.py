from __future__ import annotations

from app.domain.parse_models import ExtractionChunk


# Short output hint only; full schema is enforced via response_format in the adapter.
EXTRACTION_OUTPUT_HINT = (
    "Output: a JSON array of action objects (fixed field set per schema version). "
    "If the chunk contains no extractable actions, return []."
)

EXTRACTION_TASK_DESCRIPTION = """
Extract atomic action-centric facts from the chunk.

What counts as an extractable action:
1. A concrete action performed by a person, role, system, or service.
2. A permission or prohibition tied to an action.
3. A state transition caused by an action or system behavior.
4. An automatic system behavior that changes or processes an object.
5. A validation or restriction only if it directly affects whether an action can happen.

What does NOT count:
1. Section titles, themes, or broad process names.
2. Vague summaries such as "request processing" or "working with requests".
3. Background information without a concrete action.
4. Entities mentioned without any actionable fact.

Extraction rules:
1. Each JSON object must represent one independent action fact.
2. Prefer specific verbs like "create", "approve", "reject", "send", "assign", "change".
3. Use the closest supported wording from the chunk for verb, primary_actor, primary_object, and states.
4. If a field is not stated and not obvious from immediate local context, use null.
5. Do not invent missing actors, objects, or states.
6. If one sentence contains multiple distinct actions, output multiple objects.
7. If a permission/prohibition is expressed, extract the underlying action verb if clear.
8. Keep action_label short and human-readable.
""".strip()


EXTRACTION_NORMALIZATION_DESCRIPTION = """
Normalization rules for suggested_*_canonical fields:
1. Be conservative: normalize only when the meaning is clear.
2. Use short English snake_case forms.
3. suggested_verb_canonical should usually be a base verb such as "create", "approve", "reject", "assign".
4. suggested_object_canonical should usually be a short noun phrase such as "request", "user_account", "invoice".
5. suggested_actor_canonical should usually be a short role/system label such as "user", "manager", "billing_service".
6. suggested_state_canonical should usually be a short state label such as "draft", "approved", "rejected", "pending_review".
7. Do not merge distinct roles or objects into one canonical form unless the chunk clearly treats them as the same thing.
""".strip()


EXTRACTION_FEW_SHOTS = """
Examples:

Text:
"The user submits the request. After validation, the system changes the request status to approved."

Output:
[
  {
    "verb": "submits",
    "primary_object": "request",
    "primary_actor": "user",
    "input_state": null,
    "output_state": "submited",
    "action_label": "user submits request",
    "suggested_actor_canonical": "user",
    "suggested_object_canonical": "request",
    "suggested_verb_canonical": "submit",
    "suggested_state_canonical": "submited"
  },
  {
    "verb": "changes status",
    "primary_object": "request",
    "primary_actor": "system",
    "input_state": "submited",
    "output_state": "approved",
    "action_label": "system approves request",
    "suggested_actor_canonical": "system",
    "suggested_object_canonical": "request",
    "suggested_verb_canonical": "approve",
    "suggested_state_canonical": "approved"
  }
]

Text:
"Managers cannot edit closed orders."

Output:
[
  {
    "verb": "edit",
    "primary_object": "orders",
    "primary_actor": "Managers",
    "input_state": "closed",
    "output_state": null,
    "action_label": "manager cannot edit closed order",
    "suggested_actor_canonical": "manager",
    "suggested_object_canonical": "order",
    "suggested_verb_canonical": "edit",
    "suggested_state_canonical": "closed"
  }
]
""".strip()


def build_extraction_messages(
    chunk: ExtractionChunk,
    prompt_version: str,
    schema_version: str,
    normalization_hint: str | None = None,
) -> list[dict[str, str]]:
    section_path_str = " > ".join(chunk.section_path) if chunk.section_path else "(root)"

    chunk_meta = (
        f"Chunk ID: {chunk.chunk_id}\n"
        f"Section path: {section_path_str}\n"
        f"Estimated tokens: {chunk.estimated_tokens}\n"
        f"Prompt version: {prompt_version}\n"
        f"Schema version: {schema_version}"
    )

    norm_guidance = normalization_hint.strip() if normalization_hint else EXTRACTION_NORMALIZATION_DESCRIPTION

    system_content = (
        "You extract structured action facts from business and system documents.\n\n"
        f"{EXTRACTION_OUTPUT_HINT}\n\n"
        f"{EXTRACTION_TASK_DESCRIPTION}\n\n"
        f"{norm_guidance}\n\n"
        f"{EXTRACTION_FEW_SHOTS}"
    )

    user_content = (
        f"{chunk_meta}\n\n"
        "Extract actions from the chunk below.\n"
        "Return JSON only.\n\n"
        "---\n\n"
        f"{chunk.chunk_text}"
    )

    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]