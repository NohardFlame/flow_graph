"""Internal representations for parsed documents and extraction chunks.

Used by the parser adapter and chunk assembler; not tied to Docling internals.
"""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from app.core.types import DocumentId, RunId


class BlockType(StrEnum):
    """Type of a structural unit in a parsed document."""

    PARAGRAPH = "paragraph"
    LIST = "list"
    TABLE = "table"
    NOTE = "note"
    HEADING = "heading"


@dataclass(frozen=True)
class SectionUnit:
    """A single structural unit (paragraph, list, table, etc.) with provenance."""

    section_path: list[str]
    block_type: BlockType
    text: str
    source_spans: dict[str, Any]
    page_refs: list[dict[str, Any]]


@dataclass
class ParsedDocument:
    """Structured result of document parsing, independent of parser implementation."""

    document_id: DocumentId
    run_id: RunId
    source_format: str
    title: str
    sections: list[SectionUnit]
    tables: list[dict[str, Any]]
    lists: list[dict[str, Any]]
    raw_docling_export_ref: dict[str, Any] | None = None


def merge_parsed_documents(
    document_id: DocumentId,
    run_id: RunId,
    parsed_docs: list[ParsedDocument],
) -> ParsedDocument:
    """Merge multiple ParsedDocuments into one. Section paths are prefixed with part index to keep chunk IDs unique."""
    if not parsed_docs:
        return ParsedDocument(
            document_id=document_id,
            run_id=run_id,
            source_format="multi",
            title="",
            sections=[],
            tables=[],
            lists=[],
            raw_docling_export_ref=None,
        )
    merged_sections: list[SectionUnit] = []
    for i, doc in enumerate(parsed_docs):
        prefix = ["part", str(i)]
        for u in doc.sections:
            merged_sections.append(
                SectionUnit(
                    section_path=prefix + list(u.section_path),
                    block_type=u.block_type,
                    text=u.text,
                    source_spans=dict(u.source_spans),
                    page_refs=list(u.page_refs),
                )
            )
    all_tables: list[dict[str, Any]] = []
    all_lists: list[dict[str, Any]] = []
    for doc in parsed_docs:
        all_tables.extend(doc.tables)
        all_lists.extend(doc.lists)
    first = parsed_docs[0]
    return ParsedDocument(
        document_id=document_id,
        run_id=run_id,
        source_format="multi" if len(parsed_docs) > 1 else first.source_format,
        title=first.title or "",
        sections=merged_sections,
        tables=all_tables,
        lists=all_lists,
        raw_docling_export_ref=None,
    )


@dataclass(frozen=True)
class ExtractionChunk:
    """A single extraction window for LLM or prefilter; chunk_id is deterministic."""

    chunk_id: str
    section_path: list[str]
    chunk_text: str
    source_spans: dict[str, Any]
    page_refs: list[dict[str, Any]]
    estimated_tokens: int
    structural_features: dict[str, Any] = field(default_factory=dict)
