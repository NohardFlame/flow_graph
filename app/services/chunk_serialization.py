"""Serialize ExtractionChunk to LLM-ready text: title, section path, no page furniture."""

from app.domain.parse_models import ExtractionChunk


def chunk_to_llm_text(chunk: ExtractionChunk, document_title: str | None = None) -> str:
    """Format chunk for LLM input: document title, section path, chunk text. No page furniture."""
    parts: list[str] = []
    if document_title:
        parts.append(f"Document: {document_title}")
    if chunk.section_path:
        parts.append("Section: " + " / ".join(chunk.section_path))
    parts.append(chunk.chunk_text)
    return "\n\n".join(parts)
