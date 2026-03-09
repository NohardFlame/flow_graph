"""Reserved-word and empty-slug handling."""

import pytest

from app.core.errors import NormalizationError
from app.core.normalization.reserved import check_reserved


def test_check_reserved_valid_slug_returns_unchanged() -> None:
    slug, warnings = check_reserved("valid_slug", set(), field_name="actor")
    assert slug == "valid_slug"
    assert warnings == []


def test_check_reserved_empty_no_fallback_raises() -> None:
    with pytest.raises(NormalizationError, match="empty and no fallback"):
        check_reserved("", set(), field_name="actor")


def test_check_reserved_empty_with_fallback_returns_fallback() -> None:
    slug, warnings = check_reserved("", set(), fallback="unknown_actor", field_name="actor")
    assert slug == "unknown_actor"
    assert len(warnings) == 1
    assert "empty" in warnings[0]
    assert "unknown_actor" in warnings[0]


def test_check_reserved_reserved_word_no_fallback_raises() -> None:
    with pytest.raises(NormalizationError, match="reserved and not allowed"):
        check_reserved("reserved_word", {"reserved_word"}, field_name="object")


def test_check_reserved_reserved_word_with_fallback_returns_fallback() -> None:
    slug, warnings = check_reserved(
        "reserved_word", {"reserved_word"}, fallback="unknown_object", field_name="object"
    )
    assert slug == "unknown_object"
    assert len(warnings) == 1
    assert "reserved" in warnings[0]
