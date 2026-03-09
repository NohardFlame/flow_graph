"""Build Action and ActionEvidence from NormalizedActionRecord for persistence."""

from typing import Any

from app.core.protocols import IdGeneratorProtocol
from app.db.models import Action, ActionEvidence
from app.domain.normalization_models import NormalizedActionRecord

# Max snippet length for evidence
EVIDENCE_SNIPPET_MAX_CHARS = 2000


def build_action_entities(
    run_id: str,
    chunk_id: str | None,
    normalized_record: NormalizedActionRecord,
    *,
    raw_json: dict[str, Any] | None = None,
    confidence: float | None = None,
    id_generator: IdGeneratorProtocol,
    snippet: str = "",
    section_path: list[str] | None = None,
    page_refs: list[dict[str, Any]] | None = None,
) -> tuple[Action, list[ActionEvidence]]:
    """Build one Action and zero or one ActionEvidence from a NormalizedActionRecord.

    Idempotency is handled by ActionRepository.save (upsert by run_id, action_canonical).
    """
    action_id = id_generator.generate()
    action_label = (
        (normalized_record.surface_forms.get("action_label") or "").strip()
        or normalized_record.action_canonical
    )
    def _trunc256(s: str | None) -> str | None:
        if s is None or not s:
            return None
        return s[:256]

    def _trunc512(s: str) -> str:
        return (s or "")[:512]

    action = Action(
        id=action_id,
        run_id=run_id,
        chunk_id=chunk_id,
        action_label=_trunc512(action_label),
        action_canonical=_trunc512(normalized_record.action_canonical),
        primary_actor_key=_trunc256(normalized_record.primary_actor_key),
        primary_object_key=_trunc256(normalized_record.primary_object_key),
        input_state_key=_trunc256(normalized_record.input_state_key),
        output_state_key=_trunc256(normalized_record.output_state_key),
        confidence=confidence,
        raw_jsonb=raw_json,
        normalization_version=normalized_record.normalization_version or None,
    )
    evidence_list: list[ActionEvidence] = []
    if snippet or section_path or page_refs:
        ev_snippet = (snippet[:EVIDENCE_SNIPPET_MAX_CHARS]) if snippet else action_label[:500]
        ev_id = id_generator.generate()
        ev = ActionEvidence(
            id=ev_id,
            action_id=action_id,
            snippet=ev_snippet,
            section_path_jsonb={"path": section_path} if section_path else None,
            page_refs_jsonb={"refs": page_refs} if page_refs else None,
        )
        evidence_list.append(ev)
    return action, evidence_list
