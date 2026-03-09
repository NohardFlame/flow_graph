"""Lexical (TF-IDF) score tests."""

import pytest

from app.services.prefilter.features.lexical import lexical_scores


def test_lexical_scores_empty_chunks():
    assert lexical_scores([], ["query"]) == []
    assert lexical_scores(["a"], []) == [0.0]


def test_lexical_scores_relative_ordering():
    chunks = [
        "User action is required to submit the form.",
        "The weather is nice today.",
    ]
    queries = ["user action", "submit"]
    scores = lexical_scores(chunks, queries)
    assert len(scores) == 2
    assert scores[0] >= scores[1]
    assert scores[0] > 0


def test_lexical_scores_deterministic():
    chunks = ["Permission to edit is granted."]
    queries = ["permission"]
    a = lexical_scores(chunks, queries)
    b = lexical_scores(chunks, queries)
    assert a == b
