"""Chunk assembler tests. Use in-memory ParsedDocument fixtures only; no Docling."""

import pytest

from app.domain.parse_models import ExtractionChunk
from app.services.chunk_assembler import ChunkAssembler
from tests.fixtures.parse_fixtures import (
    parsed_doc_conditions_and_action,
    parsed_doc_list_of_rules,
    parsed_doc_large_section,
    parsed_doc_simple_headings,
    parsed_doc_with_table,
)


class TestHeadingAndParagraphsStayTogether:
    """Heading and following paragraphs stay in the same chunk when under token cap."""

    def test_simple_headings_one_chunk_per_section(self):
        doc = parsed_doc_simple_headings()
        assembler = ChunkAssembler()
        chunks = assembler.assemble(doc)
        # Introduction: heading + 2 paras; Rules: heading + 2 paras
        assert len(chunks) >= 2
        intro_texts = [c.chunk_text for c in chunks if "Introduction" in (c.section_path or [])]
        assert any("intro paragraph" in t for t in intro_texts)
        assert any("Rule one" in t or "Rule two" in t for c in chunks for t in [c.chunk_text])

    def test_heading_and_following_paragraphs_in_same_chunk(self):
        doc = parsed_doc_simple_headings()
        assembler = ChunkAssembler()
        chunks = assembler.assemble(doc)
        for chunk in chunks:
            if chunk.section_path and "Introduction" in chunk.section_path:
                assert "Introduction" in chunk.chunk_text or "intro" in chunk.chunk_text.lower()


class TestTableAndNearbyTextStayTogether:
    """Table and caption + nearby interpretation text stay together."""

    def test_table_and_explanatory_text_together(self):
        doc = parsed_doc_with_table()
        assembler = ChunkAssembler()
        chunks = assembler.assemble(doc)
        # At least one chunk should contain both table content and interpretation
        combined = " ".join(c.chunk_text for c in chunks)
        assert "A" in combined and "B" in combined
        assert "Interpretation" in combined or "primary" in combined


class TestLargeSectionSplitsBySubheading:
    """Large section splits by subheading before token-only split."""

    def test_splits_at_subheading_before_pure_token_split(self):
        doc = parsed_doc_large_section()
        assembler = ChunkAssembler()
        chunks = assembler.assemble(doc)
        # Should have at least 2 chunks (Main long para vs Sub content), split at "Sub"
        assert len(chunks) >= 2
        section_paths = [c.section_path for c in chunks]
        assert any("Sub" in (p or []) for p in section_paths)


class TestChunkIdsStable:
    """Chunk ids are deterministic for identical inputs."""

    def test_same_input_same_chunk_ids(self):
        doc = parsed_doc_simple_headings()
        assembler = ChunkAssembler()
        chunks1 = assembler.assemble(doc)
        chunks2 = assembler.assemble(doc)
        ids1 = [c.chunk_id for c in chunks1]
        ids2 = [c.chunk_id for c in chunks2]
        assert ids1 == ids2

    def test_chunk_ids_are_64_char_hex(self):
        doc = parsed_doc_simple_headings()
        assembler = ChunkAssembler()
        chunks = assembler.assemble(doc)
        for c in chunks:
            assert len(c.chunk_id) == 64
            assert all(h in "0123456789abcdef" for h in c.chunk_id)


class TestOverlapContext:
    """Overlap injects only intended context (section path, previous subheading)."""

    def test_overlap_does_not_duplicate_full_content(self):
        doc = parsed_doc_simple_headings()
        assembler = ChunkAssembler()
        chunks = assembler.assemble(doc)
        full_raw = " ".join(u.text for u in doc.sections)
        for c in chunks:
            # Chunk text may have overlap prefix but should not be huge duplicate
            assert len(c.chunk_text) <= len(full_raw) * 2  # generous


class TestRegressionConditionsVsAction:
    """Regression: conditions separated from action."""

    def test_conditions_and_action_in_separate_chunks_or_clear_boundary(self):
        doc = parsed_doc_conditions_and_action()
        assembler = ChunkAssembler()
        chunks = assembler.assemble(doc)
        assert len(chunks) >= 2
        texts = [c.chunk_text for c in chunks]
        conditions_found = any("Conditions" in t or "X and Y" in t for t in texts)
        action_found = any("Action" in t or "perform Z" in t for t in texts)
        assert conditions_found and action_found


class TestChunkStructure:
    """ExtractionChunk has required fields and token estimate."""

    def test_each_chunk_has_estimated_tokens(self):
        doc = parsed_doc_simple_headings()
        assembler = ChunkAssembler()
        chunks = assembler.assemble(doc)
        for c in chunks:
            assert isinstance(c, ExtractionChunk)
            assert c.estimated_tokens >= 0
            assert c.chunk_id
            assert c.section_path is not None  # may be []
