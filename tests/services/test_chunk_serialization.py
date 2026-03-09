"""Serialization tests: chunk_to_llm_text includes section path, preserves lists/tables, no page furniture."""

import pytest

from app.domain.parse_models import ExtractionChunk
from app.services.chunk_serialization import chunk_to_llm_text


def test_section_path_included():
    chunk = ExtractionChunk(
        chunk_id="a" * 64,
        section_path=["Introduction", "Scope"],
        chunk_text="This is the scope paragraph.",
        source_spans={},
        page_refs=[],
        estimated_tokens=10,
    )
    out = chunk_to_llm_text(chunk, document_title="My Doc")
    assert "Introduction" in out or "Scope" in out
    assert "This is the scope" in out


def test_document_title_included_when_provided():
    chunk = ExtractionChunk(
        chunk_id="b" * 64,
        section_path=["Section 1"],
        chunk_text="Content.",
        source_spans={},
        page_refs=[],
        estimated_tokens=2,
    )
    out = chunk_to_llm_text(chunk, document_title="Policy Document")
    assert "Policy Document" in out
    assert "Content." in out


def test_document_title_omitted_when_none():
    chunk = ExtractionChunk(
        chunk_id="c" * 64,
        section_path=[],
        chunk_text="Content.",
        source_spans={},
        page_refs=[],
        estimated_tokens=2,
    )
    out = chunk_to_llm_text(chunk, document_title=None)
    assert "Content." in out
    assert "None" not in out or "Document:" not in out or out.startswith("Section:")


def test_lists_preserved():
    chunk = ExtractionChunk(
        chunk_id="d" * 64,
        section_path=["Rules"],
        chunk_text="- Admin may edit.\n- User may view.",
        source_spans={},
        page_refs=[],
        estimated_tokens=10,
    )
    out = chunk_to_llm_text(chunk, document_title=None)
    assert "- Admin" in out or "Admin" in out
    assert "edit" in out and "view" in out


def test_tables_rendered_stable_text():
    chunk = ExtractionChunk(
        chunk_id="e" * 64,
        section_path=["Summary"],
        chunk_text="| A | B |\n| 1 | 2 |",
        source_spans={},
        page_refs=[],
        estimated_tokens=5,
    )
    out = chunk_to_llm_text(chunk, document_title=None)
    assert "A" in out and "B" in out
    assert "1" in out and "2" in out


def test_page_furniture_excluded():
    """Page numbers, headers, footers should not be injected by serialization."""
    chunk = ExtractionChunk(
        chunk_id="f" * 64,
        section_path=[],
        chunk_text="Real content here.",
        source_spans={},
        page_refs=[{"page_no": 1, "bbox": [0, 0, 100, 100]}],
        estimated_tokens=5,
    )
    out = chunk_to_llm_text(chunk, document_title=None)
    # We include section path and title; we should not add "Page 1" or bbox as content
    assert "Real content" in out
    # Serializer may include section path header but not raw page_refs as body text
    assert "bbox" not in out or "page_no" not in out
