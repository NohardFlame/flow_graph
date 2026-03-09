"""Docling-based document parser adapter. Maps to ParsedDocument and raises ParsingError on failure."""

import tempfile
from pathlib import Path
from typing import Any

from app.core.types import DocumentId, RunId
from app.domain.parse_models import BlockType, ParsedDocument, SectionUnit
from app.core.errors import ParsingError


# Content types we support via convert_string (no temp file)
_MARKDOWN_CT = {"text/markdown", "text/x-markdown", "application/octet-stream"}
_HTML_CT = {"text/html", "application/xhtml+xml"}


class DoclingParserAdapter:
    """Implements DocumentParserProtocol using Docling. Requires document_id and run_id for ParsedDocument."""

    def __init__(
        self,
        document_id: DocumentId = "",
        run_id: RunId = "",
    ) -> None:
        self._document_id = document_id
        self._run_id = run_id

    def parse(
        self,
        source: bytes | str,
        content_type: str | None = None,
    ) -> ParsedDocument:
        """Convert source to ParsedDocument. Raises ParsingError on failure."""
        try:
            from docling.document_converter import DocumentConverter
            from docling.datamodel.base_models import InputFormat
        except ImportError as e:
            raise ParsingError(f"Docling not available: {e}") from e

        converter = DocumentConverter()
        content_type = (content_type or "").split(";")[0].strip().lower()

        if isinstance(source, str):
            if content_type in _MARKDOWN_CT or not content_type:
                format_in = InputFormat.MD
            elif content_type in _HTML_CT:
                format_in = InputFormat.HTML
            else:
                raise ParsingError(f"Unsupported content type for string input: {content_type!r}")
            try:
                result = converter.convert_string(content=source, format=format_in, name="document")
            except Exception as e:
                raise ParsingError(str(e)) from e
        else:
            # bytes: write to temp file then convert
            suffix = _suffix_from_content_type(content_type)
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(source)
                    tmp_path = Path(tmp.name)
                try:
                    result = converter.convert(str(tmp_path))
                finally:
                    tmp_path.unlink(missing_ok=True)
            except Exception as e:
                raise ParsingError(str(e)) from e

        doc = result.document
        sections: list[SectionUnit] = []
        section_path: list[str] = []
        tables_export: list[dict[str, Any]] = []

        try:
            for item, level in doc.iterate_items():
                text = getattr(item, "text", None) or ""
                label_str = ""
                if hasattr(item, "label"):
                    label_str = str(getattr(item, "label", "")).lower()
                path = section_path[:level] if 1 <= level <= len(section_path) else section_path
                block_type = BlockType.PARAGRAPH
                source_spans: dict[str, Any] = {}
                page_refs = _page_refs_from_item(item)

                if "title" in label_str or "section_header" in label_str:
                    block_type = BlockType.HEADING
                    if text:
                        path = (path[: level - 1] if level >= 1 else []) + [text]
                    section_path = path
                elif hasattr(item, "export_to_dataframe"):
                    try:
                        df = item.export_to_dataframe(doc=doc)
                        text = df.to_markdown() if hasattr(df, "to_markdown") else str(df)
                        block_type = BlockType.TABLE
                        tables_export.append({"text": text})
                    except Exception:
                        pass
                # For TEXT and others, section_path stays as current (from last heading)

                if text or block_type == BlockType.HEADING:
                    unit = SectionUnit(
                        section_path=section_path,
                        block_type=block_type,
                        text=text,
                        source_spans=source_spans,
                        page_refs=page_refs,
                    )
                    sections.append(unit)
        except Exception as e:
            raise ParsingError(f"Failed to extract structure: {e}") from e

        # Fallback: if no sections, use export_to_markdown as one big paragraph
        if not sections and hasattr(doc, "export_to_markdown"):
            md = doc.export_to_markdown()
            if md and md.strip():
                sections = [
                    SectionUnit(
                        section_path=[],
                        block_type=BlockType.PARAGRAPH,
                        text=md.strip(),
                        source_spans={},
                        page_refs=[],
                    )
                ]

        raw_export: dict[str, Any] | None = None
        try:
            if hasattr(doc, "export_to_dict"):
                raw_export = doc.export_to_dict()
        except Exception:
            raw_export = None

        title = ""
        if sections and sections[0].block_type == BlockType.HEADING:
            title = sections[0].text
        elif raw_export and isinstance(raw_export.get("title"), str):
            title = raw_export["title"]

        return ParsedDocument(
            document_id=self._document_id,
            run_id=self._run_id,
            source_format=content_type or "unknown",
            title=title,
            sections=sections,
            tables=tables_export,
            lists=[],  # Could be derived from sections with block_type LIST
            raw_docling_export_ref=raw_export,
        )


def _page_refs_from_item(item: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    prov = getattr(item, "prov", None)
    if not prov:
        return out
    for p in (prov if hasattr(prov, "__iter__") and not isinstance(prov, str) else [prov]):
        if hasattr(p, "page_no"):
            out.append({"page_no": getattr(p, "page_no", None)})
    return out


def _suffix_from_content_type(content_type: str) -> str:
    if not content_type:
        return ".bin"
    ct = content_type.split(";")[0].strip().lower()
    m = {"application/pdf": ".pdf", "text/plain": ".txt", "text/markdown": ".md", "text/html": ".html"}
    return m.get(ct, ".bin")
