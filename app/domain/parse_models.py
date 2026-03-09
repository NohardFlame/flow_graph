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
