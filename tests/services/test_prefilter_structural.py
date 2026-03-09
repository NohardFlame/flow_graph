"""Structural feature extraction tests."""

import pytest

from app.domain.parse_models import ExtractionChunk
from app.services.prefilter.features.structural import structural_features
from tests.fixtures.prefilter_fixtures import (
    chunk_fixture,
    fixture_glossary_noise,
    fixture_intro_noise,
    fixture_table_based_rule,
)


def test_structural_heading_relevant_boosts():
    chunk = chunk_fixture(
        "Some text.",
        section_path=["Process", "Validation"],
    )
    components, flags = structural_features(chunk, ["process", "validation"])
    assert components["heading_relevant"] == 1.0
    assert flags["heading_contains_relevant_term"] is True


def test_structural_heading_irrelevant_no_boost():
    chunk = chunk_fixture("Some text.", section_path=["Misc", "Other"])
    components, flags = structural_features(chunk, ["process", "validation"])
    assert components["heading_relevant"] == 0.0
    assert flags["heading_contains_relevant_term"] is False


def test_structural_has_table_list():
    chunk = fixture_table_based_rule()
    components, flags = structural_features(chunk, [])
    assert components["has_table_list"] == 1.0
    assert flags["has_list"] is True


def test_structural_appendix_penalty():
    chunk = fixture_glossary_noise()
    components, flags = structural_features(chunk, [])
    assert components["appendix_penalty"] == 1.0  # 1.0 so weight -0.2 applies as penalty
    assert flags["is_appendix_or_glossary_or_intro"] is True


def test_structural_intro_penalty():
    chunk = fixture_intro_noise()
    components, flags = structural_features(chunk, [])
    assert components["appendix_penalty"] == 1.0


def test_structural_depth_score():
    chunk = chunk_fixture("Text", section_path=["A", "B", "C"], section_depth=3)
    components, _ = structural_features(chunk, [])
    assert components["depth_score"] > 0
    assert components["depth_score"] <= 1.0
