"""Fixtures for normalization tests: config data and sample extraction drafts."""

from pathlib import Path

from app.core.normalization_config import NormalizationConfig, load_normalization_config
from app.domain.normalization_models import ExtractionDraft


def config_from_memory(
    role_aliases: dict[str, str] | None = None,
    object_aliases: dict[str, str] | None = None,
    verb_rewrites: dict[str, str] | None = None,
    state_rewrites: dict[str, str] | None = None,
    reserved: set[str] | None = None,
    version: str = "v1",
) -> NormalizationConfig:
    """Build NormalizationConfig from in-memory dicts (for tests). Keys should be slug form."""
    return NormalizationConfig(
        role_aliases=role_aliases or {},
        object_aliases=object_aliases or {},
        verb_rewrites=verb_rewrites or {},
        state_rewrites=state_rewrites or {},
        reserved=reserved or set(),
        version=version,
    )


def fixture_config_with_aliases() -> NormalizationConfig:
    """Config with role and object aliases for alias tests."""
    return config_from_memory(
        role_aliases={"user": "applicant", "admin": "administrator"},
        object_aliases={"form": "application_form", "doc": "document"},
        verb_rewrites={"submit": "submit", "send": "submit"},
        state_rewrites={"draft": "draft", "pending": "pending"},
        reserved={"reserved_word"},
        version="fixture_v1",
    )


def fixture_config_reserved_only() -> NormalizationConfig:
    """Config with only reserved set (no aliases)."""
    return config_from_memory(
        reserved={"empty", "null", "unknown"},
        version="reserved_v1",
    )


def fixture_draft_minimal() -> ExtractionDraft:
    """Minimal draft: verb and object only."""
    return ExtractionDraft(
        verb="Submit",
        primary_object="form",
        primary_actor=None,
        input_state=None,
        output_state=None,
    )


def fixture_draft_full() -> ExtractionDraft:
    """Full draft with all fields and suggested canonicals."""
    return ExtractionDraft(
        verb="Submit",
        primary_object="Application Form",
        primary_actor="User",
        input_state="draft",
        output_state="submitted",
        action_label="User submits the application form",
        suggested_actor_canonical="user",
        suggested_object_canonical="form",
        suggested_verb_canonical="submit",
        suggested_state_canonical="submitted",
    )


def fixture_draft_multilingual() -> ExtractionDraft:
    """Draft with non-ASCII surface forms (for transliteration tests)."""
    return ExtractionDraft(
        verb="Soumettre",
        primary_object="formulaire",
        primary_actor="Utilisateur",
        input_state="brouillon",
        output_state="soumis",
        action_label="L'utilisateur soumet le formulaire",
    )


def fixture_draft_missing_object() -> ExtractionDraft:
    """Draft with verb but no primary object (tests fallback)."""
    return ExtractionDraft(
        verb="Approve",
        primary_object=None,
        primary_actor="Admin",
    )


def fixture_draft_two_same_canonical() -> list[ExtractionDraft]:
    """Two drafts that normalize to same action_canonical (for collision tests)."""
    return [
        ExtractionDraft(verb="Submit", primary_object="form", action_label="Submit form"),
        ExtractionDraft(verb="submit", primary_object="Form", action_label="Submit the form"),
    ]


def get_fixture_config_dir() -> Path:
    """Path to a directory with fixture config files (for loader tests)."""
    return Path(__file__).resolve().parent / "normalization_config_fixture"
