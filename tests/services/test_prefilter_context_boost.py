"""Context boost: co-occurrence of signal types."""

import pytest

from app.services.prefilter.features.context_boost import context_boost_score


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
