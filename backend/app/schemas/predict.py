from __future__ import annotations

import uuid
from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field

from app.db.models import Prediction
from app.schemas.common import CacheStatus, Probabilities, Sentiment, TopWord


class PredictRequest(BaseModel):
    # Unknown fields are rejected so client typos ("txt") fail loudly instead of being ignored.
    model_config = ConfigDict(extra="forbid")

    text: str = Field(
        description=(
            "The post to analyse. Leading/trailing whitespace is ignored. "
            "At most MAX_TEXT_LENGTH characters (default 1000)."
        ),
        examples=["@united my flight was delayed 3 hours and nobody told us anything #fail"],
    )


class PredictResponse(BaseModel):
    id: uuid.UUID
    text: str = Field(description="The submitted text with surrounding whitespace removed.")
    sentiment: Sentiment
    confidence: float = Field(description="Probability of the predicted label (0-1).")
    probabilities: Probabilities
    top_words: list[TopWord] = Field(description="Words in the text that pushed the model towards its answer.")
    is_low_confidence: bool = Field(description="True when confidence is below LOW_CONFIDENCE_THRESHOLD.")
    model_version: str
    cache_status: CacheStatus
    latency_ms: float = Field(description="Time to produce the prediction (cache lookup + inference).")
    created_at: datetime

    @classmethod
    def from_row(cls, row: Prediction, low_confidence_threshold: float) -> Self:
        return cls(**cls._fields_from_row(row, low_confidence_threshold))

    @staticmethod
    def _fields_from_row(row: Prediction, low_confidence_threshold: float) -> dict:
        return {
            "id": row.id,
            "text": row.text,
            "sentiment": row.sentiment,
            "confidence": row.confidence,
            "probabilities": Probabilities(
                negative=row.prob_negative, neutral=row.prob_neutral, positive=row.prob_positive
            ),
            "top_words": row.top_words,
            # Computed on read, so changing the threshold applies to history as well.
            "is_low_confidence": row.confidence < low_confidence_threshold,
            "model_version": row.model_version,
            "cache_status": row.cache_status,
            "latency_ms": row.latency_ms,
            "created_at": row.created_at,
        }


# --- Batch -------------------------------------------------------------------------------

class BatchRowResult(BaseModel):
    row: int = Field(description="1-based data row number in the CSV (the header is not counted).")
    text: str
    sentiment: Sentiment | None = None
    confidence: float | None = None
    cache_status: CacheStatus | None = None
    id: uuid.UUID | None = Field(default=None, description="Id of the stored prediction, if the row succeeded.")
    error: str | None = Field(default=None, description="Why the row was rejected, if it failed.")


class SentimentCounts(BaseModel):
    negative: int = 0
    neutral: int = 0
    positive: int = 0


class CacheCounts(BaseModel):
    hit: int = 0
    miss: int = 0
    bypass: int = 0


class BatchResponse(BaseModel):
    batch_id: uuid.UUID
    total_rows: int
    succeeded: int
    failed: int
    summary: SentimentCounts
    cache: CacheCounts
    model_version: str
    results: list[BatchRowResult]
