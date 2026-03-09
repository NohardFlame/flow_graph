"""Section-aware chunk assembly from ParsedDocument. Deterministic chunk_id."""

from dataclasses import dataclass
from typing import Any

from app.core.checksum import sha256_hex
from app.core.token_estimate import estimated_tokens
from app.domain.parse_models import BlockType, ExtractionChunk, ParsedDocument, SectionUnit


# Preferred extraction window: 1.5k–4k tokens (spec)
DEFAULT_TOKEN_TARGET_MIN = 1500
DEFAULT_TOKEN_TARGET_MAX = 4000


@dataclass
class ChunkAssemblerConfig:
    """Optional config for chunk assembly."""

    token_target_min: int = DEFAULT_TOKEN_TARGET_MIN
    token_target_max: int = DEFAULT_TOKEN_TARGET_MAX
    overlap_prev_heading_chars: int = 80  # carry-over context


class ChunkAssembler:
    """Build extraction-oriented chunks from ParsedDocument. No Docling dependency."""

    def __init__(self, config: ChunkAssemblerConfig | None = None) -> None:
        self._config = config or ChunkAssemblerConfig()

    def assemble(self, doc: ParsedDocument) -> list[ExtractionChunk]:
        """Produce ordered ExtractionChunks with deterministic chunk_id and token estimate."""
        if not doc.sections:
            return []

        groups = self._group_units(doc.sections)
        flat_chunks: list[tuple[list[str], str, list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]] = []
        prev_heading = ""

        for path_prefix, units in groups:
            group_text = "\n\n".join(u.text for u in units)
            group_tokens = estimated_tokens(group_text)
            section_path = path_prefix or (units[0].section_path if units else [])

            if group_tokens <= self._config.token_target_max:
                text = group_text
                if prev_heading and self._config.overlap_prev_heading_chars:
                    overlap = prev_heading[: self._config.overlap_prev_heading_chars]
                    text = f"[Context: {overlap}]\n\n{text}"
                page_refs = []
                source_spans: dict[str, Any] = {}
                for u in units:
                    page_refs.extend(u.page_refs)
                    if u.source_spans:
                        source_spans.setdefault("units", []).append(u.source_spans)
                features = self._structural_features(units)
                flat_chunks.append((section_path, text, source_spans, page_refs, features))
            else:
                # Split by subheading first: if units have different section_path depths, split there
                sub_groups = self._split_by_subheading(units)
                for sub_units in sub_groups:
                    sub_text = "\n\n".join(u.text for u in sub_units)
                    sub_tokens = estimated_tokens(sub_text)
                    sub_path = sub_units[0].section_path if sub_units else section_path
                    if sub_tokens <= self._config.token_target_max:
                        text = sub_text
                        if prev_heading and self._config.overlap_prev_heading_chars:
                            overlap = prev_heading[: self._config.overlap_prev_heading_chars]
                            text = f"[Context: {overlap}]\n\n{text}"
                        page_refs = []
                        source_spans = {}
                        for u in sub_units:
                            page_refs.extend(u.page_refs)
                            if u.source_spans:
                                source_spans.setdefault("units", []).append(u.source_spans)
                        features = self._structural_features(sub_units)
                        flat_chunks.append((sub_path, text, source_spans, page_refs, features))
                    else:
                        # Token-only split
                        parts = self._split_by_tokens(sub_text, sub_path, sub_units)
                        for part_path, part_text, part_spans, part_refs, part_features in parts:
                            if prev_heading and self._config.overlap_prev_heading_chars:
                                overlap = prev_heading[: self._config.overlap_prev_heading_chars]
                                part_text = f"[Context: {overlap}]\n\n{part_text}"
                            flat_chunks.append((part_path, part_text, part_spans, part_refs, part_features))

            if units:
                last_heading = next(
                    (u.text for u in reversed(units) if u.block_type == BlockType.HEADING),
                    prev_heading,
                )
                if last_heading:
                    prev_heading = last_heading

        result: list[ExtractionChunk] = []
        for idx, (path, text, spans, refs, features) in enumerate(flat_chunks):
            tokens = estimated_tokens(text)
            chunk_id = self._deterministic_chunk_id(path, text, idx)
            result.append(
                ExtractionChunk(
                    chunk_id=chunk_id,
                    section_path=path,
                    chunk_text=text,
                    source_spans=spans,
                    page_refs=refs,
                    estimated_tokens=tokens,
                    structural_features=features,
                )
            )
        return result

    def _group_units(
        self,
        sections: list[SectionUnit],
    ) -> list[tuple[list[str], list[SectionUnit]]]:
        """Group consecutive units into semantic groups (heading+paras, table+paras, list)."""
        if not sections:
            return []

        groups: list[tuple[list[str], list[SectionUnit]]] = []
        current_path: list[str] = []
        current: list[SectionUnit] = []

        for u in sections:
            path = u.section_path or []
            if not current:
                current_path = path
                current.append(u)
                continue
            # Same section path or same prefix (subheading): keep together if same "block group"
            same_section = path == current_path or (
                len(path) >= len(current_path) and path[: len(current_path)] == current_path
            )
            if same_section and self._same_semantic_group(current[-1], u):
                current.append(u)
            else:
                if current:
                    groups.append((current_path, current))
                current_path = path
                current = [u]

        if current:
            groups.append((current_path, current))
        return groups

    def _same_semantic_group(self, prev: SectionUnit, next_u: SectionUnit) -> bool:
        """Heading+paragraph, table+paragraph, list+list stay together."""
        if next_u.block_type == BlockType.HEADING:
            return False
        if prev.block_type == BlockType.HEADING and next_u.block_type in (
            BlockType.PARAGRAPH,
            BlockType.LIST,
            BlockType.TABLE,
        ):
            return True
        if prev.block_type == BlockType.TABLE and next_u.block_type == BlockType.PARAGRAPH:
            return True
        if prev.block_type == BlockType.LIST and next_u.block_type == BlockType.LIST:
            return True
        if prev.block_type == BlockType.PARAGRAPH and next_u.block_type == BlockType.PARAGRAPH:
            return prev.section_path == next_u.section_path
        return prev.section_path == next_u.section_path and prev.block_type == next_u.block_type

    def _split_by_subheading(self, units: list[SectionUnit]) -> list[list[SectionUnit]]:
        """Split units at subheading boundaries."""
        result: list[list[SectionUnit]] = []
        current: list[SectionUnit] = []
        for u in units:
            if u.block_type == BlockType.HEADING and current and current[0].section_path != u.section_path:
                if current:
                    result.append(current)
                current = [u]
            else:
                current.append(u)
        if current:
            result.append(current)
        return result if result else [units]

    def _split_by_tokens(
        self,
        text: str,
        section_path: list[str],
        units: list[SectionUnit],
    ) -> list[tuple[list[str], str, dict[str, Any], list[dict[str, Any]], dict[str, Any]]]:
        """Split text by approximate token count; preserve section_path and features per part."""
        max_tokens = self._config.token_target_max
        approx_chars = max_tokens * 4
        parts: list[tuple[list[str], str, dict[str, Any], list[dict[str, Any]], dict[str, Any]]] = []
        start = 0
        while start < len(text):
            end = min(start + approx_chars, len(text))
            if end < len(text):
                # Break at paragraph boundary
                last_para = text.rfind("\n\n", start, end + 1)
                if last_para > start:
                    end = last_para + 2
            part_text = text[start:end].strip()
            if part_text:
                source_spans: dict[str, Any] = {}
                page_refs: list[dict[str, Any]] = []
                features = self._structural_features(units)
                parts.append((section_path, part_text, source_spans, page_refs, features))
            start = end
        return parts

    def _structural_features(self, units: list[SectionUnit]) -> dict[str, Any]:
        """Features for prefilter (Phase 6)."""
        has_table = any(u.block_type == BlockType.TABLE for u in units)
        has_list = any(u.block_type == BlockType.LIST for u in units)
        depth = len(units[0].section_path) if units else 0
        return {
            "has_table": has_table,
            "has_list": has_list,
            "section_depth": depth,
        }

    def _deterministic_chunk_id(self, section_path: list[str], chunk_text: str, index: int) -> str:
        """Deterministic 64-char hex id for (path, text, index). Used as chunk_hash in DB."""
        payload = f"{repr(section_path)}:{chunk_text}:{index}"
        return sha256_hex(payload.encode("utf-8"))
