"""Create the predictions table.

Revision ID: 0001
Revises:
Create Date: 2026-10-21
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "predictions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("text_sha256", sa.CHAR(64), nullable=False),
        sa.Column("sentiment", sa.String(16), nullable=False),
        sa.Column("confidence", sa.Double(), nullable=False),
        sa.Column("prob_negative", sa.Double(), nullable=False),
        sa.Column("prob_neutral", sa.Double(), nullable=False),
        sa.Column("prob_positive", sa.Double(), nullable=False),
        sa.Column("top_words", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("model_version", sa.String(64), nullable=False),
        sa.Column("cache_status", sa.String(8), nullable=False),
        sa.Column("source", sa.String(8), nullable=False, server_default="single"),
        sa.Column("batch_id", sa.Uuid(), nullable=True),
        sa.Column("latency_ms", sa.Double(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("sentiment IN ('negative', 'neutral', 'positive')", name="ck_predictions_sentiment"),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_predictions_confidence_range"),
        sa.CheckConstraint("cache_status IN ('hit', 'miss', 'bypass')", name="ck_predictions_cache_status"),
        sa.CheckConstraint("source IN ('single', 'batch')", name="ck_predictions_source"),
    )
    # Newest-first listing and date-range filters.
    op.create_index("ix_predictions_created_at", "predictions", [sa.text("created_at DESC")])
    # Sentiment filter combined with a date range, sorted by date.
    op.create_index("ix_predictions_sentiment_created_at", "predictions", ["sentiment", sa.text("created_at DESC")])
    op.create_index("ix_predictions_model_version", "predictions", ["model_version"])
    op.create_index("ix_predictions_batch_id", "predictions", ["batch_id"])


def downgrade() -> None:
    op.drop_index("ix_predictions_batch_id", table_name="predictions")
    op.drop_index("ix_predictions_model_version", table_name="predictions")
    op.drop_index("ix_predictions_sentiment_created_at", table_name="predictions")
    op.drop_index("ix_predictions_created_at", table_name="predictions")
    op.drop_table("predictions")
