"""Exact phrase matching tests."""

import pytest

from app.services.prefilter.features.exact_match import find_matches, normalize_text


def test_normalize_text():
    assert normalize_text("  Foo  Bar  ") == "foo bar"


def test_find_matches_finds_after_normalization():
    text = "The user may submit the form."
    lexicons = {"permission_terms": ["may"], "action_verbs": ["submit"], "role_nouns": ["user"]}
    matched, counts = find_matches(text, lexicons)
    assert "may" in matched
    assert "submit" in matched
    assert "user" in matched
    assert counts.get("permission_terms", 0) >= 1
    assert counts.get("action_verbs", 0) >= 1


def test_find_matches_empty_lexicons():
    matched, counts = find_matches("hello world", {})
    assert matched == []
    assert counts == {}


def test_find_matches_no_match():
    matched, counts = find_matches("hello world", {"action_verbs": ["perform", "execute"]})
    assert matched == []
    assert counts == {}


def test_find_matches_russian_stem_in_full_form():
    """Russian stem in lexicon matches text containing a full word form (substring match)."""
    text = "Пользователю разрешается копировать документ."
    lexicons = {"permission_terms": ["разреш"], "action_verbs": ["копир"], "object_domain_terms": ["документ"]}
    matched, counts = find_matches(text, lexicons)
    assert "разреш" in matched or any("разреш" in m for m in matched)
    assert counts.get("permission_terms", 0) >= 1
    assert counts.get("action_verbs", 0) >= 1
    assert counts.get("object_domain_terms", 0) >= 1
