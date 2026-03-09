"""Input and output models for normalization and identity.

ExtractionDraft is the shape expected from LLM extraction; NormalizedActionRecord
is the deterministic output with canonical keys, aliases, and warnings.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CollisionRecord:
    """Two or more surface forms mapped to the same canonical key."""

    canonical_key: str
    key_type: str  # e.g. "actor", "object", "action", "state"
    surface_forms: tuple[str, ...]
    merged: bool = False  # True only if configured rule allowed merge


@dataclass
class ExtractionDraft:
    """Raw extracted fields from LLM (or test fixture). All optional where spec allows fallback."""

    verb: str | None = None
    primary_object: str | None = None
    primary_actor: str | None = None
    input_state: str | None = None
    output_state: str | None = None
    # Optional human-readable label and model-suggested canonical (not used as final truth)
    action_label: str | None = None
    suggested_actor_canonical: str | None = None
    suggested_object_canonical: str | None = None
    suggested_verb_canonical: str | None = None
    suggested_state_canonical: str | None = None


@dataclass
class NormalizedActionRecord:
    """Output of normalization: canonical keys, preserved surface forms, aliases, warnings."""

    # Final computed canonical keys (used for persistence / upsert)
    action_canonical: str
    primary_actor_key: str | None
    primary_object_key: str | None
    input_state_key: str | None
    output_state_key: str | None

    # Original surface forms (preserved)
    surface_forms: dict[str, str] = field(default_factory=dict)  # e.g. "actor" -> "User", "object" -> "Form"

    # Model-suggested canonical forms (for audit; not used as final key)
    suggested_canonical: dict[str, str] = field(default_factory=dict)

    # All surface forms and aliases that contributed to this record
    aliases: list[str] = field(default_factory=list)

    # Warnings (ambiguous mapping, reserved repair, etc.)
    warnings: list[str] = field(default_factory=list)

    # Collisions: multiple surface forms -> one key
    collisions: list[CollisionRecord] = field(default_factory=list)

    normalization_version: str = ""
