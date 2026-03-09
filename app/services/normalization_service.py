"""Orchestrates normalization: config, slug, alias, reserved check, key building.

Produces NormalizedActionRecord from ExtractionDraft. Collision detection across
multiple drafts is done by normalize_batch.
"""

from __future__ import annotations

from typing import Callable

from app.core.normalization import (
    build_action_key,
    build_actor_key,
    build_object_key,
    build_state_key,
    check_reserved,
    default_transliterate,
    slugify,
)
from app.core.normalization_config import NormalizationConfig
from app.domain.normalization_models import (
    CollisionRecord,
    ExtractionDraft,
    NormalizedActionRecord,
)


# Default fallbacks when slug is empty or reserved
DEFAULT_FALLBACK_ACTOR = "unknown_actor"
DEFAULT_FALLBACK_OBJECT = "unknown_object"
DEFAULT_FALLBACK_VERB = "unknown_verb"
DEFAULT_FALLBACK_STATE = "unknown_state"


def _normalize_field(
    raw: str | None,
    config: NormalizationConfig,
    transliterate: Callable[[str], str],
    resolve: Callable[[str], str],
    reserved_fallback: str | None,
    field_name: str,
) -> tuple[str, list[str]]:
    """Slug -> transliterate -> resolve alias -> check reserved. Returns (final_slug, warnings)."""
    if raw is None or not raw.strip():
        if reserved_fallback is not None:
            return reserved_fallback, [f"{field_name} was empty; using fallback {reserved_fallback!r}"]
        return "", []
    text = transliterate(raw.strip())
    slug = slugify(text)
    if not slug:
        if reserved_fallback is not None:
            return reserved_fallback, [f"{field_name} normalized to empty; using fallback {reserved_fallback!r}"]
        return "", []
    resolved = resolve(slug)
    final, warnings = check_reserved(
        resolved,
        config.reserved,
        fallback=reserved_fallback,
        field_name=field_name,
    )
    return final, warnings


def normalize(
    draft: ExtractionDraft,
    config: NormalizationConfig,
    *,
    transliterate: Callable[[str], str] | None = None,
    fallback_actor: str = DEFAULT_FALLBACK_ACTOR,
    fallback_object: str = DEFAULT_FALLBACK_OBJECT,
    fallback_verb: str = DEFAULT_FALLBACK_VERB,
    fallback_state: str = DEFAULT_FALLBACK_STATE,
) -> NormalizedActionRecord:
    """Produce a single NormalizedActionRecord from one ExtractionDraft."""
    trans = transliterate if transliterate is not None else default_transliterate
    all_warnings: list[str] = []
    surface_forms: dict[str, str] = {}
    suggested: dict[str, str] = {}
    aliases: list[str] = []

    def add_surface(key: str, value: str | None) -> None:
        if value is not None and value.strip():
            surface_forms[key] = value.strip()

    add_surface("verb", draft.verb)
    add_surface("primary_object", draft.primary_object)
    add_surface("primary_actor", draft.primary_actor)
    add_surface("input_state", draft.input_state)
    add_surface("output_state", draft.output_state)
    if draft.action_label:
        surface_forms["action_label"] = draft.action_label.strip()

    if draft.suggested_actor_canonical:
        suggested["actor"] = draft.suggested_actor_canonical.strip()
    if draft.suggested_object_canonical:
        suggested["object"] = draft.suggested_object_canonical.strip()
    if draft.suggested_verb_canonical:
        suggested["verb"] = draft.suggested_verb_canonical.strip()
    if draft.suggested_state_canonical:
        suggested["state"] = draft.suggested_state_canonical.strip()

    verb_slug, w1 = _normalize_field(
        draft.verb,
        config,
        trans,
        config.resolve_verb,
        fallback_verb,
        "verb",
    )
    all_warnings.extend(w1)

    object_slug, w2 = _normalize_field(
        draft.primary_object,
        config,
        trans,
        config.resolve_object,
        fallback_object,
        "primary_object",
    )
    all_warnings.extend(w2)

    actor_slug, w3 = _normalize_field(
        draft.primary_actor,
        config,
        trans,
        config.resolve_role,
        fallback_actor,
        "primary_actor",
    )
    all_warnings.extend(w3)

    primary_object_key = build_object_key(object_slug)
    primary_actor_key = build_actor_key(actor_slug)
    action_canonical = build_action_key(verb_slug, primary_object_key)

    input_state_slug, w4 = _normalize_field(
        draft.input_state,
        config,
        trans,
        config.resolve_state,
        fallback_state,
        "input_state",
    )
    all_warnings.extend(w4)
    input_state_key: str | None = (
        build_state_key(primary_object_key, input_state_slug) if input_state_slug else None
    )
    if draft.input_state and draft.input_state.strip():
        aliases.append(draft.input_state.strip())

    output_state_slug, w5 = _normalize_field(
        draft.output_state,
        config,
        trans,
        config.resolve_state,
        fallback_state,
        "output_state",
    )
    all_warnings.extend(w5)
    output_state_key = (
        build_state_key(primary_object_key, output_state_slug) if output_state_slug else None
    )
    if draft.output_state and draft.output_state.strip():
        aliases.append(draft.output_state.strip())

    for v in [draft.verb, draft.primary_object, draft.primary_actor]:
        if v and v.strip():
            aliases.append(v.strip())

    return NormalizedActionRecord(
        action_canonical=action_canonical,
        primary_actor_key=primary_actor_key,
        primary_object_key=primary_object_key,
        input_state_key=input_state_key,
        output_state_key=output_state_key,
        surface_forms=surface_forms,
        suggested_canonical=suggested,
        aliases=aliases,
        warnings=all_warnings,
        collisions=[],
        normalization_version=config.version,
    )


def normalize_batch(
    drafts: list[ExtractionDraft],
    config: NormalizationConfig,
    *,
    transliterate: Callable[[str], str] | None = None,
    fallback_actor: str = DEFAULT_FALLBACK_ACTOR,
    fallback_object: str = DEFAULT_FALLBACK_OBJECT,
    fallback_verb: str = DEFAULT_FALLBACK_VERB,
    fallback_state: str = DEFAULT_FALLBACK_STATE,
) -> tuple[list[NormalizedActionRecord], list[CollisionRecord]]:
    """Normalize multiple drafts; detect collisions when two drafts map to same action_canonical."""
    records = [
        normalize(
            d,
            config,
            transliterate=transliterate,
            fallback_actor=fallback_actor,
            fallback_object=fallback_object,
            fallback_verb=fallback_verb,
            fallback_state=fallback_state,
        )
        for d in drafts
    ]
    # Group by action_canonical to find collisions
    by_canonical: dict[str, list[NormalizedActionRecord]] = {}
    for r in records:
        by_canonical.setdefault(r.action_canonical, []).append(r)

    collisions: list[CollisionRecord] = []
    for canonical, group in by_canonical.items():
        if len(group) <= 1:
            continue
        seen: set[str] = set()
        unique_forms: list[str] = []
        for rec in group:
            for alias in rec.aliases:
                if alias and alias not in seen:
                    seen.add(alias)
                    unique_forms.append(alias)
            label = rec.surface_forms.get("action_label")
            if label and label not in seen:
                seen.add(label)
                unique_forms.append(label)
        if not unique_forms:
            unique_forms = [rec.action_canonical for rec in group]
        collisions.append(
            CollisionRecord(
                canonical_key=canonical,
                key_type="action",
                surface_forms=tuple(unique_forms),
                merged=False,
            )
        )
    return records, collisions
