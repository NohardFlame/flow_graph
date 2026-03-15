"""Helpers for extraction: expand selected chunks with context, batch by context window."""

from __future__ import annotations

from app.core.checksum import sha256_hex
from app.db.models import Chunk


def _path_list(c: Chunk) -> list[str]:
    """Return section path as list from Chunk.section_path_jsonb."""
    sp = c.section_path_jsonb
    if isinstance(sp, list):
        return sp
    if isinstance(sp, dict):
        return list(sp.get("path") or [])
    return []


def expand_with_context_chunks(
    all_chunks: list[Chunk],
    selected_chunks: list[Chunk],
    n_levels_up: int,
) -> list[Chunk]:
    """Add parent-level context chunks for each selected chunk. Preserves document order.

    For each selected chunk, include up to n_levels_up chunks that are hierarchically
    above it (section_path is a prefix). When multiple chunks share the same parent path,
    include the one that immediately precedes the selected chunk in document order.
    If n_levels_up is 0 or chunk is top-level, no context is added.
    """
    if n_levels_up <= 0 or not selected_chunks:
        return list(selected_chunks)
    order_index = {c.id: i for i, c in enumerate(all_chunks)}
    selected_ids = {c.id for c in selected_chunks}
    context_ids: set[str] = set()
    for s in selected_chunks:
        idx = order_index.get(s.id)
        if idx is None:
            continue
        path = _path_list(s)
        for k in range(1, min(n_levels_up, len(path)) + 1):
            parent_path = path[:-k]
            for i in range(idx - 1, -1, -1):
                c = all_chunks[i]
                if _path_list(c) == parent_path:
                    context_ids.add(c.id)
                    break
    included = selected_ids | context_ids
    return [c for c in all_chunks if c.id in included]


def batch_chunks_for_context(
    chunks: list[Chunk],
    max_input_tokens: int,
    system_prompt_tokens: int,
    user_message_overhead_tokens: int = 100,
) -> list[list[Chunk]]:
    """Split chunks into batches that fit within max_input_tokens (system + user content)."""
    if not chunks:
        return []
    available = max_input_tokens - system_prompt_tokens - user_message_overhead_tokens
    if available <= 0:
        return [[c] for c in chunks]
    batches: list[list[Chunk]] = []
    current: list[Chunk] = []
    current_tokens = 0
    for c in chunks:
        tok = c.estimated_tokens or 0
        if current and current_tokens + tok > available:
            batches.append(current)
            current = []
            current_tokens = 0
        current.append(c)
        current_tokens += tok
    if current:
        batches.append(current)
    return batches


def build_batch_chunk_hash(chunk_hashes: list[str]) -> str:
    """Deterministic chunk_hash for a glued batch. Fits in 64 chars (chunk_hash column)."""
    payload = ",".join(sorted(chunk_hashes)).encode("utf-8")
    h = sha256_hex(payload)
    return "glued_" + h[:58]
