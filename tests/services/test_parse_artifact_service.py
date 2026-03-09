"""Tests for parse artifact persistence (debug artifacts to storage)."""

import json

import pytest

from app.domain.parse_models import BlockType, ExtractionChunk, ParsedDocument, SectionUnit
from app.services.parse_artifact_service import save_parse_artifacts
from tests.services.conftest import fake_storage


def test_save_parse_artifacts_writes_docling_and_chunk_manifest(fake_storage):
    doc = ParsedDocument(
        document_id="doc1",
        run_id="run1",
        source_format="markdown",
        title="Test",
        sections=[
            SectionUnit(
                section_path=["Intro"],
                block_type=BlockType.PARAGRAPH,
                text="Hello.",
                source_spans={},
                page_refs=[],
            ),
        ],
        tables=[],
        lists=[],
    )
    chunks = [
        ExtractionChunk(
            chunk_id="a" * 64,
            section_path=["Intro"],
            chunk_text="Hello.",
            source_spans={},
            page_refs=[],
            estimated_tokens=2,
        ),
    ]
    save_parse_artifacts(fake_storage, "doc1", "run1", doc, chunks)
    assert "parsed/doc1/run1/docling.json" in fake_storage._store
    assert "parsed/doc1/run1/chunk_manifest.json" in fake_storage._store
    body_docling, _, _ = fake_storage._store["parsed/doc1/run1/docling.json"]
    data = json.loads(body_docling.decode("utf-8"))
    assert data["document_id"] == "doc1"
    assert data["title"] == "Test"
    body_manifest, _, _ = fake_storage._store["parsed/doc1/run1/chunk_manifest.json"]
    manifest = json.loads(body_manifest.decode("utf-8"))
    assert len(manifest) == 1
    assert manifest[0]["chunk_id"] == "a" * 64


def test_save_parse_artifacts_with_markdown_optional(fake_storage):
    doc = ParsedDocument(
        document_id="d2",
        run_id="r2",
        source_format="md",
        title="X",
        sections=[],
        tables=[],
        lists=[],
    )
    save_parse_artifacts(fake_storage, "d2", "r2", doc, [], markdown_body="# Markdown\n\nBody.")
    assert "parsed/d2/r2/markdown" not in fake_storage._store
    assert "parsed/d2/r2/document.md" in fake_storage._store
    body, _, _ = fake_storage._store["parsed/d2/r2/document.md"]
    assert b"# Markdown" in body
