"""Docling parser adapter tests. Real Docling on fixture markdown; failure maps to ParsingError."""

import pytest

from app.core.errors import ParsingError
from app.domain.parse_models import BlockType, ParsedDocument
from app.adapters.parser.docling_adapter import DoclingParserAdapter


# Mark tests that require Docling (heavy); can skip if DOCLING_SKIP=1 or import fails
DOCLING_AVAILABLE = False
try:
    from docling.document_converter import DocumentConverter  # noqa: F401
    DOCLING_AVAILABLE = True
except ImportError:
    pass


@pytest.mark.skipif(not DOCLING_AVAILABLE, reason="Docling not installed")
class TestDoclingAdapterSupportedFile:
    """Supported file/content converts successfully."""

    def test_markdown_string_converts_to_parsed_document(self):
        adapter = DoclingParserAdapter(document_id="d1", run_id="r1")
        content = "# Introduction\n\nThis is the intro.\n\n## Rules\n\n- Rule one.\n- Rule two."
        result = adapter.parse(content, content_type="text/markdown")
        assert isinstance(result, ParsedDocument)
        assert result.document_id == "d1"
        assert result.run_id == "r1"
        assert result.source_format
        assert len(result.sections) >= 2
        headings = [u for u in result.sections if u.block_type == BlockType.HEADING]
        assert len(headings) >= 1
        assert any("Introduction" in u.text for u in result.sections)

    def test_parse_export_contains_expected_top_level_structure(self):
        adapter = DoclingParserAdapter(document_id="d2", run_id="r2")
        content = "# Title\n\nParagraph."
        result = adapter.parse(content, content_type="text/markdown")
        assert result.title or any(u.block_type == BlockType.HEADING for u in result.sections)
        assert result.sections
        assert result.source_format


@pytest.mark.skipif(not DOCLING_AVAILABLE, reason="Docling not installed")
class TestDoclingAdapterParseFailure:
    """Parse failure maps to ParsingError."""

    def test_unsupported_content_type_raises_parsing_error(self):
        adapter = DoclingParserAdapter(document_id="d3", run_id="r3")
        with pytest.raises(ParsingError) as exc_info:
            adapter.parse(b"binary \x00\x01\x02", content_type="application/weird-unsupported")
        assert "Unsupported" in str(exc_info.value) or "failed" in str(exc_info.value).lower() or "ParsingError" in type(exc_info.value).__name__

    def test_malformed_input_can_raise_parsing_error(self):
        adapter = DoclingParserAdapter(document_id="d4", run_id="r4")
        # Empty or invalid might be accepted or rejected; if rejected, must be ParsingError
        try:
            result = adapter.parse("", content_type="text/markdown")
            assert result.sections is not None  # may be []
        except ParsingError:
            pass  # acceptable


class TestDoclingAdapterWithoutDocling:
    """When Docling is not available, parse raises ParsingError (no leak)."""

    @pytest.mark.skipif(DOCLING_AVAILABLE, reason="Docling is installed; testing no-leak when missing")
    def test_parse_raises_parsing_error_when_docling_missing(self):
        adapter = DoclingParserAdapter(document_id="d5", run_id="r5")
        with pytest.raises(ParsingError):
            adapter.parse("# Hi", content_type="text/markdown")
