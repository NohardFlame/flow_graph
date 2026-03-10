"""Chunk persistence. Idempotent by (run_id, chunk_hash).

Callers should pass the deterministic chunk_id from chunk assembly (ExtractionChunk.chunk_id)
as chunk_hash, so that the same parse and chunking config yields the same hash and upserts
are idempotent.
"""

import uuid
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db.models import Chunk


class ChunkRepository:
    """Persistence for extraction chunks. Uses upsert for idempotency by (run_id, chunk_hash)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert_chunk(
        self,
        run_id: str,
        chunk_hash: str,
        text: str,
        *,
        section_path: dict[str, Any] | None = None,
        page_refs: dict[str, Any] | None = None,
        estimated_tokens: int | None = None,
        prefilter_score: float | None = None,
        prefilter_decision: str | None = None,
        prefilter_features: dict[str, Any] | None = None,
    ) -> Chunk:
        chunk_id = str(uuid.uuid4())
        stmt = insert(Chunk).values(
            id=chunk_id,
            run_id=run_id,
            chunk_hash=chunk_hash,
            text=text,
            section_path_jsonb=section_path,
            page_refs_jsonb=page_refs,
            estimated_tokens=estimated_tokens,
            prefilter_score=prefilter_score,
            prefilter_decision=prefilter_decision,
            prefilter_features_jsonb=prefilter_features,
        ).on_conflict_do_update(
            index_elements=["run_id", "chunk_hash"],
            set_=dict(
                text=text,
                section_path_jsonb=section_path,
                page_refs_jsonb=page_refs,
                estimated_tokens=estimated_tokens,
                prefilter_score=prefilter_score,
                prefilter_decision=prefilter_decision,
                prefilter_features_jsonb=prefilter_features,
            ),
        )
        self._session.execute(stmt)
        self._session.flush()
        row = self._session.execute(
            select(Chunk).where(Chunk.run_id == run_id, Chunk.chunk_hash == chunk_hash)
        ).scalar_one()
        return row

    def list_by_run(
        self, run_id: str, limit: int | None = None, offset: int = 0
    ) -> list[Chunk]:
        q = select(Chunk).where(Chunk.run_id == run_id).order_by(Chunk.id).offset(offset)
        if limit is not None:
            q = q.limit(limit)
        result = self._session.execute(q)
        return list(result.scalars().all())

    def count_by_run(self, run_id: str) -> int:
        """Return total number of chunks for the run (for pagination)."""
        result = self._session.execute(
            select(func.count()).select_from(Chunk).where(Chunk.run_id == run_id)
        )
        return result.scalar_one() or 0

    def list_by_run_and_decision(self, run_id: str, decision: str) -> list[Chunk]:
        result = self._session.execute(
            select(Chunk).where(Chunk.run_id == run_id, Chunk.prefilter_decision == decision).order_by(Chunk.id)
        )
        return list(result.scalars().all())

    def list_by_run_for_extraction(self, run_id: str) -> list[Chunk]:
        """Return chunks that should be sent to the LLM: keep, or gray with selected_for_llm true."""
        keep = Chunk.prefilter_decision == "keep"
        gray_selected = (Chunk.prefilter_decision == "gray") & (
            Chunk.prefilter_features_jsonb.op("->>")("selected_for_llm") == "true"
        )
        result = self._session.execute(
            select(Chunk).where(Chunk.run_id == run_id, or_(keep, gray_selected)).order_by(Chunk.id)
        )
        return list(result.scalars().all())
