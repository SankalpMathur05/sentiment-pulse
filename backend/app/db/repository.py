"""Every database query lives here, written with SQLAlchemy expressions (always parameterised).

Aggregations are done by Postgres (COUNT / AVG / GROUP BY), so analytics cost does not
grow with the amount of Python work per row.
"""
from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.db.models import Prediction

Granularity = Literal["hour", "day"]


@dataclass(frozen=True)
class PredictionFilters:
    sentiment: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None


@dataclass(frozen=True)
class Overview:
    total: int
    unique_texts: int
    average_confidence: float | None
    low_confidence_count: int
    first_at: datetime | None
    last_at: datetime | None


@dataclass(frozen=True)
class TimeseriesBucket:
    bucket: datetime
    negative: int
    neutral: int
    positive: int


def _apply_filters(stmt: Select, filters: PredictionFilters) -> Select:
    if filters.sentiment is not None:
        stmt = stmt.where(Prediction.sentiment == filters.sentiment)
    if filters.date_from is not None:
        stmt = stmt.where(Prediction.created_at >= filters.date_from)
    if filters.date_to is not None:
        stmt = stmt.where(Prediction.created_at <= filters.date_to)
    return stmt


# --- Writes ------------------------------------------------------------------------------

def save_predictions(session: Session, rows: Sequence[Prediction]) -> None:
    """Insert rows in one transaction. SQLAlchemy 2.x sends many rows as batched multi-row
    INSERTs ("insertmanyvalues"), so a 500-row CSV is not 500 round trips."""
    session.add_all(rows)
    session.commit()


# --- Reads -------------------------------------------------------------------------------

def get_prediction(session: Session, prediction_id: uuid.UUID) -> Prediction | None:
    return session.get(Prediction, prediction_id)


def list_predictions(
    session: Session, filters: PredictionFilters, page: int, page_size: int
) -> tuple[list[Prediction], int]:
    """One page of predictions (newest first) plus the total number matching the filters."""
    total = session.scalar(_apply_filters(select(func.count()).select_from(Prediction), filters)) or 0
    stmt = (
        _apply_filters(select(Prediction), filters)
        # id breaks ties between rows with the same timestamp, so pages never overlap.
        .order_by(Prediction.created_at.desc(), Prediction.id.desc())
        .limit(page_size)
        .offset((page - 1) * page_size)
    )
    return list(session.scalars(stmt)), total


def get_overview(session: Session, filters: PredictionFilters, low_confidence_threshold: float) -> Overview:
    stmt = select(
        func.count().label("total"),
        func.count(func.distinct(Prediction.text_sha256)).label("unique_texts"),
        func.avg(Prediction.confidence).label("average_confidence"),
        func.count().filter(Prediction.confidence < low_confidence_threshold).label("low_confidence_count"),
        func.min(Prediction.created_at).label("first_at"),
        func.max(Prediction.created_at).label("last_at"),
    ).select_from(Prediction)
    row = session.execute(_apply_filters(stmt, filters)).one()
    return Overview(
        total=row.total,
        unique_texts=row.unique_texts,
        average_confidence=float(row.average_confidence) if row.average_confidence is not None else None,
        low_confidence_count=row.low_confidence_count,
        first_at=row.first_at,
        last_at=row.last_at,
    )


def count_by_sentiment(session: Session, filters: PredictionFilters) -> dict[str, int]:
    stmt = select(Prediction.sentiment, func.count()).group_by(Prediction.sentiment)
    return {sentiment: count for sentiment, count in session.execute(_apply_filters(stmt, filters))}


def count_by_cache_status(session: Session, filters: PredictionFilters) -> dict[str, int]:
    stmt = select(Prediction.cache_status, func.count()).group_by(Prediction.cache_status)
    return {status: count for status, count in session.execute(_apply_filters(stmt, filters))}


def count_by_model_version(session: Session, filters: PredictionFilters) -> list[tuple[str, int]]:
    count = func.count().label("count")
    stmt = (
        select(Prediction.model_version, count)
        .group_by(Prediction.model_version)
        .order_by(count.desc(), Prediction.model_version)
    )
    return [(version, total) for version, total in session.execute(_apply_filters(stmt, filters))]


def sentiment_timeseries(
    session: Session, filters: PredictionFilters, granularity: Granularity
) -> list[TimeseriesBucket]:
    """Counts per sentiment per hour/day bucket (UTC), oldest first. Only buckets with data."""
    bucket = func.date_trunc(granularity, Prediction.created_at, "UTC").label("bucket")
    stmt = (
        select(
            bucket,
            func.count().filter(Prediction.sentiment == "negative").label("negative"),
            func.count().filter(Prediction.sentiment == "neutral").label("neutral"),
            func.count().filter(Prediction.sentiment == "positive").label("positive"),
        )
        .group_by(bucket)
        .order_by(bucket)
    )
    return [
        TimeseriesBucket(bucket=row.bucket, negative=row.negative, neutral=row.neutral, positive=row.positive)
        for row in session.execute(_apply_filters(stmt, filters))
    ]
