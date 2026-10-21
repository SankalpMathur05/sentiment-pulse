"""ORM model for the `predictions` table. Must stay in sync with alembic/versions/0001."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import CHAR, CheckConstraint, DateTime, Double, Index, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Prediction(Base):
    """One prediction event. Every request is stored, including cache hits, so the table
    is an event log that analytics can aggregate (volume, cache hit rate, model versions)."""

    __tablename__ = "predictions"
    __table_args__ = (
        CheckConstraint("sentiment IN ('negative', 'neutral', 'positive')", name="ck_predictions_sentiment"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_predictions_confidence_range"),
        CheckConstraint("cache_status IN ('hit', 'miss', 'bypass')", name="ck_predictions_cache_status"),
        CheckConstraint("source IN ('single', 'batch')", name="ck_predictions_source"),
        # History list and time-range filters sort/filter by newest first.
        Index("ix_predictions_created_at", text("created_at DESC")),
        # Filtering by sentiment within a date range (dashboard filters).
        Index("ix_predictions_sentiment_created_at", "sentiment", text("created_at DESC")),
        Index("ix_predictions_model_version", "model_version"),
        Index("ix_predictions_batch_id", "batch_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    text: Mapped[str] = mapped_column(Text)
    # SHA-256 of the *normalised* text: identical posts share a hash (unique-post counts, cache key).
    text_sha256: Mapped[str] = mapped_column(CHAR(64))
    sentiment: Mapped[str] = mapped_column(String(16))
    confidence: Mapped[float] = mapped_column(Double)
    prob_negative: Mapped[float] = mapped_column(Double)
    prob_neutral: Mapped[float] = mapped_column(Double)
    prob_positive: Mapped[float] = mapped_column(Double)
    top_words: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, server_default="[]")
    model_version: Mapped[str] = mapped_column(String(64))
    cache_status: Mapped[str] = mapped_column(String(8))
    source: Mapped[str] = mapped_column(String(8), default="single", server_default="single")
    batch_id: Mapped[uuid.UUID | None]
    latency_ms: Mapped[float] = mapped_column(Double)
    # Set in Python so the value is known without reading the row back after INSERT.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, server_default=func.now())
