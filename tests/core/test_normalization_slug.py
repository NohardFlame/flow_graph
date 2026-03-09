"""Basic normalization: slugify (whitespace, punctuation, snake_case)."""

import pytest

from app.core.normalization.slug import slugify


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("", ""),
        ("   ", ""),
        ("  Foo  Bar  ", "foo_bar"),
        ("foo bar", "foo_bar"),
        ("foo-bar", "foo_bar"),
        ("foo.bar", "foo_bar"),
        ("foo, bar; baz", "foo_bar_baz"),
        ("UPPERCASE", "uppercase"),
        ("already_snake", "already_snake"),
        ("multiple   spaces", "multiple_spaces"),
        ("punctuation! and/slashes", "punctuation_and_slashes"),
        ("  leading_and_trailing  ", "leading_and_trailing"),
        ("double--dash", "double_dash"),
        ("a", "a"),
    ],
)
def test_slugify_whitespace_and_punctuation(raw: str, expected: str) -> None:
    assert slugify(raw) == expected


def test_slugify_snake_case_output() -> None:
    """Output is lowercase with single underscores only."""
    result = slugify("  Some  Mixed  Case  String  ")
    assert result == "some_mixed_case_string"
    assert " " not in result
    assert result.islower() or result == ""


def test_slugify_deterministic() -> None:
    """Same input always yields same output."""
    for raw in ["Submit Form", "  Submit   Form  ", "submit form"]:
        assert slugify(raw) == "submit_form"
