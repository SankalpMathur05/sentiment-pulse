from __future__ import annotations

import uuid
from typing import Self

from pydantic import BaseModel, Field

from app.db.models import Prediction
from app.schemas.common import PredictionSource
from app.schemas.predict import PredictResponse


class PredictionRecord(PredictResponse):
    """A stored prediction: the /api/predict response plus where it came from."""

    source: PredictionSource
    batch_id: uuid.UUID | None

    @classmethod
    def from_row(cls, row: Prediction, low_confidence_threshold: float) -> Self:
        return cls(
            **cls._fields_from_row(row, low_confidence_threshold),
            source=row.source,
            batch_id=row.batch_id,
        )


class PredictionPage(BaseModel):
    items: list[PredictionRecord]
    page: int
    page_size: int
    total: int = Field(description="Number of predictions matching the filters (all pages).")
    pages: int
