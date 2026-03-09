"""Chunk fixtures for prefilter tests. Labeled by intent for assertions."""

from app.domain.parse_models import ExtractionChunk


def chunk_fixture(
    text: str,
    *,
    chunk_id: str = "chunk-fixture-1",
    section_path: list[str] | None = None,
    has_table: bool = False,
    has_list: bool = False,
    section_depth: int = 1,
) -> ExtractionChunk:
    """Build one ExtractionChunk with optional structural features."""
    return ExtractionChunk(
        chunk_id=chunk_id,
        section_path=section_path or ["Section"],
        chunk_text=text,
        source_spans={},
        page_refs=[],
        estimated_tokens=len(text.split()),
        structural_features={
            "has_table": has_table,
            "has_list": has_list,
            "section_depth": section_depth,
        },
    )


# --- Labeled fixtures (intent for expected features) ---

def fixture_explicit_action() -> ExtractionChunk:
    """Chunk with explicit user/system action language."""
    return chunk_fixture(
        "The user must submit the form within 30 days. The system shall validate the request.",
        chunk_id="fixture-action",
        section_path=["Process", "Submission"],
        section_depth=2,
    )


def fixture_permission() -> ExtractionChunk:
    """Chunk with permission (may / allowed)."""
    return chunk_fixture(
        "Admin may edit the document. Users are allowed to view the record.",
        chunk_id="fixture-permission",
        section_path=["Permissions"],
    )


def fixture_restriction() -> ExtractionChunk:
    """Chunk with restriction (must not / prohibited)."""
    return chunk_fixture(
        "Users must not delete approved records. Modification is prohibited after approval.",
        chunk_id="fixture-restriction",
        section_path=["Restrictions"],
    )


def fixture_state_transition() -> ExtractionChunk:
    """Chunk with state/status transition."""
    return chunk_fixture(
        "When the request is submitted, the status changes from draft to pending. The workflow moves to validation.",
        chunk_id="fixture-state",
        section_path=["Workflow", "Status"],
        section_depth=2,
    )


def fixture_glossary_noise() -> ExtractionChunk:
    """Low-relevance: glossary section."""
    return chunk_fixture(
        "Term: A definition of something. Another term: another definition.",
        chunk_id="fixture-glossary",
        section_path=["Glossary"],
    )


def fixture_intro_noise() -> ExtractionChunk:
    """Low-relevance: introduction/overview."""
    return chunk_fixture(
        "This document describes the overall process. The following sections provide detail.",
        chunk_id="fixture-intro",
        section_path=["Introduction"],
    )


def fixture_table_based_rule() -> ExtractionChunk:
    """Rule expressed in table + list (structural boost)."""
    return chunk_fixture(
        "Approval rules:\n- Admin may approve.\n- User may submit.",
        chunk_id="fixture-table-rule",
        section_path=["Rules", "Approval"],
        has_list=True,
        section_depth=2,
    )


def fixture_edge_gray() -> ExtractionChunk:
    """Borderline chunk (some signals, not strong)."""
    return chunk_fixture(
        "If the condition is met, proceed to the next step. The system validates the input.",
        chunk_id="fixture-gray",
        section_path=["Procedure"],
    )


def fixture_false_positive_trap() -> ExtractionChunk:
    """Text that might match keywords but is not action-centric (e.g. narrative)."""
    return chunk_fixture(
        "The user manual describes how to use the system. The word permission appears in the overview.",
        chunk_id="fixture-fp",
        section_path=["Overview"],
    )


def fixture_condition_and_action() -> ExtractionChunk:
    """If/when condition + action (pattern match)."""
    return chunk_fixture(
        "When the request is received, the admin must approve or reject within 24 hours.",
        chunk_id="fixture-condition-action",
        section_path=["Process", "Validation"],
        section_depth=2,
    )
