"""Canonical key builders."""

import pytest

from app.core.normalization.keys import (
    build_action_key,
    build_actor_key,
    build_object_key,
    build_state_key,
)


@pytest.mark.parametrize(
    "normalized_name,expected",
    [
        ("applicant", "applicant"),
        ("administrator", "administrator"),
    ],
)
def test_build_actor_key(normalized_name: str, expected: str) -> None:
    assert build_actor_key(normalized_name) == expected


@pytest.mark.parametrize(
    "normalized_name,expected",
    [
        ("application_form", "application_form"),
        ("document", "document"),
    ],
)
def test_build_object_key(normalized_name: str, expected: str) -> None:
    assert build_object_key(normalized_name) == expected


def test_build_action_key_includes_primary_object() -> None:
    assert build_action_key("submit", "application_form") == "submit_application_form"


def test_build_action_key_same_verb_different_objects_different_keys() -> None:
    k1 = build_action_key("submit", "form")
    k2 = build_action_key("submit", "document")
    assert k1 != k2
    assert k1 == "submit_form"
    assert k2 == "submit_document"


def test_build_state_key_format() -> None:
    assert build_state_key("application_form", "draft") == "application_form__draft"
    assert build_state_key("document", "pending") == "document__pending"
