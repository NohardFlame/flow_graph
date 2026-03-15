"""SQLAlchemy 2 declarative models for the system of record."""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, Boolean, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB


class Base(DeclarativeBase):
    """Declarative base for all models."""

    pass


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    versions: Mapped[list["DocumentVersion"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    source_storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    source_parts_jsonb: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    document: Mapped["Document"] = relationship(back_populates="versions")


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    document_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    current_step: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    config_version: Mapped[str | None] = mapped_column(String(32), nullable=True)

    parsed_artifacts: Mapped[list["ParsedArtifact"]] = relationship(back_populates="run", cascade="all, delete-orphan")
    chunks: Mapped[list["Chunk"]] = relationship(back_populates="run", cascade="all, delete-orphan")
    llm_calls: Mapped[list["LLMCall"]] = relationship(back_populates="run", cascade="all, delete-orphan")
    actions: Mapped[list["Action"]] = relationship(back_populates="run", cascade="all, delete-orphan")
    run_events: Mapped[list["RunEvent"]] = relationship(back_populates="run", cascade="all, delete-orphan")


class ParsedArtifact(Base):
    __tablename__ = "parsed_artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False)
    docling_storage_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    markdown_storage_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    chunk_manifest_storage_key: Mapped[str | None] = mapped_column(String(512), nullable=True)

    run: Mapped["Run"] = relationship(back_populates="parsed_artifacts")


class Chunk(Base):
    __tablename__ = "chunks"

    __table_args__ = (UniqueConstraint("run_id", "chunk_hash", name="uq_chunks_run_id_chunk_hash"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False)
    chunk_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    section_path_jsonb: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    page_refs_jsonb: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    estimated_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prefilter_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    prefilter_decision: Mapped[str | None] = mapped_column(String(32), nullable=True)
    prefilter_features_jsonb: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    run: Mapped["Run"] = relationship(back_populates="chunks")
    llm_calls: Mapped[list["LLMCall"]] = relationship(back_populates="chunk", cascade="all, delete-orphan")
    actions: Mapped[list["Action"]] = relationship(back_populates="chunk", cascade="all, delete-orphan")


class LLMCall(Base):
    __tablename__ = "llm_calls"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False)
    chunk_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("chunks.id", ondelete="SET NULL"), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    schema_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    cache_hit: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    request_storage_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    response_storage_key: Mapped[str | None] = mapped_column(String(512), nullable=True)

    run: Mapped["Run"] = relationship(back_populates="llm_calls")
    chunk: Mapped["Chunk | None"] = relationship(back_populates="llm_calls")


class Action(Base):
    __tablename__ = "actions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False)
    chunk_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("chunks.id", ondelete="SET NULL"), nullable=True)
    action_label: Mapped[str] = mapped_column(String(512), nullable=False)
    action_canonical: Mapped[str] = mapped_column(String(512), nullable=False)
    primary_actor_key: Mapped[str | None] = mapped_column(String(256), nullable=True)
    primary_object_key: Mapped[str | None] = mapped_column(String(256), nullable=True)
    input_state_key: Mapped[str | None] = mapped_column(String(256), nullable=True)
    output_state_key: Mapped[str | None] = mapped_column(String(256), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_jsonb: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    normalization_version: Mapped[str | None] = mapped_column(String(32), nullable=True)

    run: Mapped["Run"] = relationship(back_populates="actions")
    chunk: Mapped["Chunk | None"] = relationship(back_populates="actions")
    evidence: Mapped[list["ActionEvidence"]] = relationship(back_populates="action", cascade="all, delete-orphan")


class ActionEvidence(Base):
    __tablename__ = "action_evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    action_id: Mapped[str] = mapped_column(String(36), ForeignKey("actions.id", ondelete="CASCADE"), nullable=False)
    snippet: Mapped[str] = mapped_column(Text, nullable=False)
    section_path_jsonb: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    page_refs_jsonb: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    action: Mapped["Action"] = relationship(back_populates="evidence")


class RunEvent(Base):
    __tablename__ = "run_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False)
    step: Mapped[str] = mapped_column(String(64), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_jsonb: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    run: Mapped["Run"] = relationship(back_populates="run_events")
