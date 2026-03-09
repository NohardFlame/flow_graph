"""Normalization service: full pipeline, aliases, keys, collisions, determinism."""

import pytest

from app.core.normalization.transliterate import noop_transliterate
from app.domain.normalization_models import ExtractionDraft
from app.services.normalization_service import normalize, normalize_batch
from tests.fixtures.normalization_fixtures import (
    config_from_memory,
    fixture_config_reserved_only,
    fixture_config_with_aliases,
    fixture_draft_full,
    fixture_draft_minimal,
    fixture_draft_missing_object,
    fixture_draft_multilingual,
    fixture_draft_two_same_canonical,
)


def test_normalize_minimal_draft_produces_action_key_with_object() -> None:
    """Action key includes primary object."""
    config = config_from_memory(version="v1")
    draft = fixture_draft_minimal()
    record = normalize(draft, config, transliterate=noop_transliterate)
    assert record.action_canonical == "submit_form"
    assert record.primary_object_key == "form"
    assert record.primary_actor_key == "unknown_actor"
    assert record.normalization_version == "v1"


def test_normalize_known_alias_rewrites_to_canonical() -> None:
    """Known alias rewrites to canonical form."""
    config = fixture_config_with_aliases()
    draft = ExtractionDraft(
        verb="Submit",
        primary_object="form",
        primary_actor="User",
    )
    record = normalize(draft, config, transliterate=noop_transliterate)
    assert record.primary_actor_key == "applicant"
    assert record.primary_object_key == "application_form"
    assert record.action_canonical == "submit_application_form"


def test_normalize_unknown_alias_remains_normalized_surface_form() -> None:
    """Unknown alias stays as normalized (slug) form."""
    config = config_from_memory(version="v1")
    draft = ExtractionDraft(
        verb="Approve",
        primary_object="Request",
        primary_actor="Manager",
    )
    record = normalize(draft, config, transliterate=noop_transliterate)
    assert record.primary_actor_key == "manager"
    assert record.primary_object_key == "request"
    assert record.action_canonical == "approve_request"


def test_normalize_alias_list_preserves_original_terms() -> None:
    """Aliases list includes original surface forms."""
    config = config_from_memory(version="v1")
    draft = fixture_draft_full()
    record = normalize(draft, config, transliterate=noop_transliterate)
    assert "Submit" in record.aliases or "submit" in record.aliases
    assert "Application Form" in record.aliases or "application form" in record.aliases
    assert "User" in record.aliases or "user" in record.aliases
    assert record.surface_forms.get("verb") == "Submit"
    assert record.surface_forms.get("primary_object") == "Application Form"
    assert record.surface_forms.get("primary_actor") == "User"


def test_normalize_missing_object_uses_fallback() -> None:
    """Missing primary object falls back to configured fallback."""
    config = config_from_memory(version="v1")
    draft = fixture_draft_missing_object()
    record = normalize(draft, config, transliterate=noop_transliterate)
    assert record.primary_object_key == "unknown_object"
    assert record.action_canonical == "approve_unknown_object"
    assert any("fallback" in w.lower() or "empty" in w.lower() for w in record.warnings)


def test_normalize_same_verb_different_objects_different_keys() -> None:
    """Same verb on different objects yields different action keys."""
    config = config_from_memory(version="v1")
    r1 = normalize(
        ExtractionDraft(verb="Submit", primary_object="form"),
        config,
        transliterate=noop_transliterate,
    )
    r2 = normalize(
        ExtractionDraft(verb="Submit", primary_object="document"),
        config,
        transliterate=noop_transliterate,
    )
    assert r1.action_canonical != r2.action_canonical
    assert r1.action_canonical == "submit_form"
    assert r2.action_canonical == "submit_document"


def test_normalize_batch_two_same_canonical_records_collision() -> None:
    """Two drafts that normalize to same action_canonical produce a collision record."""
    config = config_from_memory(version="v1")
    drafts = fixture_draft_two_same_canonical()
    records, collisions = normalize_batch(drafts, config, transliterate=noop_transliterate)
    assert len(records) == 2
    assert records[0].action_canonical == records[1].action_canonical
    assert records[0].action_canonical == "submit_form"
    assert len(collisions) == 1
    assert collisions[0].canonical_key == "submit_form"
    assert collisions[0].key_type == "action"
    assert len(collisions[0].surface_forms) >= 2
    assert not collisions[0].merged


def test_normalize_batch_no_collision_when_canonicals_differ() -> None:
    """No collision when all action canonicals are distinct."""
    config = config_from_memory(version="v1")
    drafts = [
        ExtractionDraft(verb="Submit", primary_object="form"),
        ExtractionDraft(verb="Approve", primary_object="document"),
    ]
    records, collisions = normalize_batch(drafts, config, transliterate=noop_transliterate)
    assert len(records) == 2
    assert len(collisions) == 0
    assert records[0].action_canonical != records[1].action_canonical


def test_normalize_reserved_with_fallback_repairs_and_warns() -> None:
    """Reserved word triggers fallback and warning."""
    config = fixture_config_reserved_only()
    draft = ExtractionDraft(
        verb="Submit",
        primary_object="empty",
        primary_actor="User",
    )
    record = normalize(
        draft,
        config,
        transliterate=noop_transliterate,
        fallback_object="unknown_object",
    )
    assert record.primary_object_key == "unknown_object"
    assert any("reserved" in w.lower() for w in record.warnings)


def test_normalize_determinism_same_input_same_output() -> None:
    """Repeated runs with same inputs yield identical output."""
    config = fixture_config_with_aliases()
    draft = fixture_draft_full()
    r1 = normalize(draft, config, transliterate=noop_transliterate)
    r2 = normalize(draft, config, transliterate=noop_transliterate)
    assert r1.action_canonical == r2.action_canonical
    assert r1.primary_actor_key == r2.primary_actor_key
    assert r1.primary_object_key == r2.primary_object_key
    assert r1.input_state_key == r2.input_state_key
    assert r1.output_state_key == r2.output_state_key
    assert r1.normalization_version == r2.normalization_version


def test_normalize_version_in_record_matches_config() -> None:
    """Normalization version in record comes from config."""
    config = config_from_memory(version="fixture_v1")
    draft = fixture_draft_minimal()
    record = normalize(draft, config, transliterate=noop_transliterate)
    assert record.normalization_version == "fixture_v1"


def test_normalize_state_keys_include_object() -> None:
    """State keys use object_key__state_name format."""
    config = config_from_memory(version="v1")
    draft = ExtractionDraft(
        verb="Submit",
        primary_object="form",
        input_state="draft",
        output_state="submitted",
    )
    record = normalize(draft, config, transliterate=noop_transliterate)
    assert record.primary_object_key == "form"
    assert record.input_state_key == "form__draft"
    assert record.output_state_key == "form__submitted"


def test_normalize_suggested_canonical_preserved_not_used_as_key() -> None:
    """Model-suggested canonical is stored for audit but final key is computed."""
    config = config_from_memory(version="v1")
    # Suggest "wrong" canonical; we should still compute from raw
    draft = ExtractionDraft(
        verb="Submit",
        primary_object="Form",
        suggested_object_canonical="wrong_object",
    )
    record = normalize(draft, config, transliterate=noop_transliterate)
    assert record.primary_object_key == "form"
    assert record.suggested_canonical.get("object") == "wrong_object"


def test_normalize_multilingual_deterministic() -> None:
    """Multilingual surface forms produce deterministic output (with noop transliterate)."""
    config = config_from_memory(version="v1")
    draft = fixture_draft_multilingual()
    r1 = normalize(draft, config, transliterate=noop_transliterate)
    r2 = normalize(draft, config, transliterate=noop_transliterate)
    assert r1.action_canonical == r2.action_canonical
    assert r1.primary_actor_key == r2.primary_actor_key
    assert r1.primary_object_key == r2.primary_object_key
