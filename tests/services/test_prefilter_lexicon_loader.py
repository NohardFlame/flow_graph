"""Lexicon loader: fail-fast and loading."""

import pytest
from pathlib import Path

from app.core.errors import ConfigError
from app.services.prefilter.lexicon_loader import (
    LEXICON_FILES,
    load_lexicon_file,
    load_lexicons,
    load_seeded_queries,
)


def test_load_lexicons_fails_if_directory_missing():
    with pytest.raises(ConfigError) as exc_info:
        load_lexicons("nonexistent_dir_xyz")
    assert "not found" in str(exc_info.value).lower() or "directory" in str(exc_info.value).lower()


def test_load_lexicons_fails_if_file_missing(tmp_path):
    # Create dir but remove one required file
    for f in LEXICON_FILES:
        (tmp_path / f).write_text("term\n", encoding="utf-8")
    (tmp_path / "seeded_queries.txt").write_text("query\n", encoding="utf-8")
    # Remove one
    (tmp_path / "action_verbs.txt").unlink()
    with pytest.raises(ConfigError) as exc_info:
        load_lexicons(tmp_path)
    assert "action_verbs" in str(exc_info.value) or "not found" in str(exc_info.value).lower()


def test_load_lexicons_succeeds_with_valid_dir():
    repo_root = Path(__file__).resolve().parent.parent.parent
    lexicon_dir = repo_root / "data" / "prefilter"
    if not lexicon_dir.is_dir():
        pytest.skip("data/prefilter not found (run from repo root)")
    lexicons, queries = load_lexicons(lexicon_dir)
    assert "action_verbs" in lexicons
    assert "heading_relevant_terms" in lexicons
    assert isinstance(lexicons["action_verbs"], list)
    assert len(queries) >= 1
    # Normalization: no empty, no comments
    for key, terms in lexicons.items():
        for t in terms:
            assert t.strip() == t
            assert t.lower() == t
            assert not t.startswith("#")


def test_load_lexicon_file_skips_comments_and_empty(tmp_path):
    (tmp_path / "test.txt").write_text("# comment\n\n  foo  \nbar\n# again\n", encoding="utf-8")
    terms = load_lexicon_file(tmp_path / "test.txt")
    assert terms == ["foo", "bar"]
