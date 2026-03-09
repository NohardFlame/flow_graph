"""Baseline schema: documents, runs, chunks, actions, run_events, etc.

Revision ID: 001
Revises:
Create Date: Baseline

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("original_filename", sa.String(512), nullable=False),
        sa.Column("content_type", sa.String(128), nullable=False),
        sa.Column("checksum_sha256", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("storage_key", sa.String(512), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "document_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("source_storage_key", sa.String(512), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_version_id", sa.String(36), sa.ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("current_step", sa.String(64), nullable=True),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("config_version", sa.String(32), nullable=True),
    )
    op.create_table(
        "parsed_artifacts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("run_id", sa.String(36), sa.ForeignKey("runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("docling_storage_key", sa.String(512), nullable=True),
        sa.Column("markdown_storage_key", sa.String(512), nullable=True),
        sa.Column("chunk_manifest_storage_key", sa.String(512), nullable=True),
    )
    op.create_table(
        "chunks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("run_id", sa.String(36), sa.ForeignKey("runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_hash", sa.String(64), nullable=False),
        sa.Column("section_path_jsonb", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("page_refs_jsonb", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("estimated_tokens", sa.Integer(), nullable=True),
        sa.Column("prefilter_score", sa.Float(), nullable=True),
        sa.Column("prefilter_decision", sa.String(32), nullable=True),
        sa.Column("prefilter_features_jsonb", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.UniqueConstraint("run_id", "chunk_hash", name="uq_chunks_run_id_chunk_hash"),
    )
    op.create_table(
        "llm_calls",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("run_id", sa.String(36), sa.ForeignKey("runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_id", sa.String(36), sa.ForeignKey("chunks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("provider", sa.String(64), nullable=True),
        sa.Column("model", sa.String(128), nullable=True),
        sa.Column("prompt_version", sa.String(32), nullable=True),
        sa.Column("schema_version", sa.String(32), nullable=True),
        sa.Column("cache_hit", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("estimated_cost_usd", sa.Float(), nullable=True),
        sa.Column("request_storage_key", sa.String(512), nullable=True),
        sa.Column("response_storage_key", sa.String(512), nullable=True),
    )
    op.create_table(
        "actions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("run_id", sa.String(36), sa.ForeignKey("runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_id", sa.String(36), sa.ForeignKey("chunks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action_label", sa.String(512), nullable=False),
        sa.Column("action_canonical", sa.String(512), nullable=False),
        sa.Column("primary_actor_key", sa.String(256), nullable=True),
        sa.Column("primary_object_key", sa.String(256), nullable=True),
        sa.Column("input_state_key", sa.String(256), nullable=True),
        sa.Column("output_state_key", sa.String(256), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("raw_jsonb", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("normalization_version", sa.String(32), nullable=True),
    )
    op.create_table(
        "action_evidence",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("action_id", sa.String(36), sa.ForeignKey("actions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("snippet", sa.Text(), nullable=False),
        sa.Column("section_path_jsonb", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("page_refs_jsonb", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_table(
        "run_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("run_id", sa.String(36), sa.ForeignKey("runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step", sa.String(64), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("payload_jsonb", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("run_events")
    op.drop_table("action_evidence")
    op.drop_table("actions")
    op.drop_table("llm_calls")
    op.drop_table("chunks")
    op.drop_table("parsed_artifacts")
    op.drop_table("runs")
    op.drop_table("document_versions")
    op.drop_table("documents")
