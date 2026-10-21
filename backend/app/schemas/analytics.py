from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import Sentiment


class SentimentShare(BaseModel):
    sentiment: Sentiment
    count: int
    percentage: float = Field(description="Share of all predictions, 0-100, rounded to 1 decimal place.")


class CacheBreakdown(BaseModel):
    hit: int
    miss: int
    bypass: int
    hit_rate: float | None = Field(
        description="hit / (hit + miss): share of cache lookups that were answered from Redis. "
        "Bypassed requests never reached the cache, so they are excluded. Null if there were no lookups."
    )


class TimeseriesPoint(BaseModel):
    bucket: datetime = Field(description="Start of the hour/day bucket (UTC).")
    negative: int
    neutral: int
    positive: int


class ModelVersionCount(BaseModel):
    model_version: str
    count: int


class AnalyticsSummary(BaseModel):
    total: int
    unique_texts: int = Field(description="Distinct posts, comparing the normalised text the model sees.")
    distribution: list[SentimentShare] = Field(description="Always negative, neutral, positive, in that order.")
    average_confidence: float | None
    low_confidence_count: int
    cache: CacheBreakdown
    granularity: Literal["hour", "day"] = Field(
        description="'hour' when the requested range (or the data, if no range) spans at most 2 days."
    )
    timeseries: list[TimeseriesPoint] = Field(description="Ascending; only buckets that contain data.")
    model_versions: list[ModelVersionCount]
