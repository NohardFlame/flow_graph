"""Context boost: co-occurrence of signal types."""

import pytest

from app.services.prefilter.features.context_boost import (
    _tokenize_for_window,
    context_boost_score,
)


def test_context_boost_action_near_object():
    text = "The user must submit the document to the system."
    score = context_boost_score(
        text,
        action_terms=["submit"],
        object_terms=["document"],
        modal_restriction_terms=[],
        role_terms=[],
        state_terms=[],
    )
    assert score > 0


def test_context_boost_no_cooccurrence():
    text = "The weather is nice."
    score = context_boost_score(
        text,
        action_terms=["submit"],
        object_terms=["document"],
        modal_restriction_terms=[],
        role_terms=[],
        state_terms=[],
    )
    assert score == 0.0


def test_context_boost_role_modal():
    text = "The admin may approve the request."
    score = context_boost_score(
        text,
        action_terms=[],
        object_terms=[],
        modal_restriction_terms=["may"],
        role_terms=["admin"],
        state_terms=[],
    )
    assert score > 0


def test_tokenize_for_window_includes_cyrillic():
    """Tokenizer produces Cyrillic tokens so Russian words participate in windows."""
    tokens = _tokenize_for_window("user может выполнить действие")
    assert "может" in tokens
    assert "выполнить" in tokens
    assert "действие" in tokens
    assert "user" in tokens


def test_context_boost_russian_stem_in_word():
    """Window containing Russian word that contains a permission stem gets boost with role stem."""
    # Use stems that are substrings of inflected forms: "пользовател" in "пользователю"/"пользователь"
    text = "Пользователю разрешается копировать документ."
    score = context_boost_score(
        text,
        action_terms=[],
        object_terms=[],
        modal_restriction_terms=["разреш"],
        role_terms=["пользовател"],
        state_terms=[],
    )
    assert score > 0
