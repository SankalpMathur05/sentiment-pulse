"""Dashboard summary: turns the repository's SQL aggregates into the API response."""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.db import repository
from app.db.repository import Granularity, PredictionFilters
from app.schemas.analytics import (
    AnalyticsSummary,
    CacheBreakdown,
    ModelVersionCount,
    SentimentShare,
    TimeseriesPoint,
)
from app.schemas.common import CacheStatus, Sentiment

# Up to two days, hourly buckets (at most 48 points); beyond that, daily buckets.
HOURLY_MAX_SPAN = timedelta(days=2)


def choose_granularity(filters: PredictionFilters, first_at: datetime | None, last_at: datetime | None) -> Granularity:
    """Use the requested range when given, otherwise the span of the matching data."""
    start = filters.date_from or first_at
    end = filters.date_to or last_at
    if start is None or end is None:
        return "hour"
    return "hour" if end - start <= HOURLY_MAX_SPAN else "day"


def build_summary(session: Session, filters: PredictionFilters, low_confidence_threshold: float) -> AnalyticsSummary:
    overview = repository.get_overview(session, filters, low_confidence_threshold)
    by_sentiment = repository.count_by_sentiment(session, filters)
    by_cache = repository.count_by_cache_status(session, filters)
    granularity = choose_granularity(filters, overview.first_at, overview.last_at)
    timeseries = repository.sentiment_timeseries(session, filters, granularity)
    model_versions = repository.count_by_model_version(session, filters)

    hits, misses = by_cache.get(CacheStatus.HIT, 0), by_cache.get(CacheStatus.MISS, 0)
    return AnalyticsSummary(
        total=overview.total,
        unique_texts=overview.unique_texts,
        # Every label is listed, even with zero predictions, so charts keep a stable shape.
        distribution=[
            SentimentShare(
                sentiment=sentiment,
                count=by_sentiment.get(sentiment, 0),
                percentage=round(100 * by_sentiment.get(sentiment, 0) / overview.total, 1) if overview.total else 0.0,
            )
            for sentiment in Sentiment
        ],
        average_confidence=(
            round(overview.average_confidence, 4) if overview.average_confidence is not None else None
        ),
        low_confidence_count=overview.low_confidence_count,
        cache=CacheBreakdown(
            hit=hits,
            miss=misses,
            bypass=by_cache.get(CacheStatus.BYPASS, 0),
            hit_rate=round(hits / (hits + misses), 4) if hits + misses else None,
        ),
        granularity=granularity,
        timeseries=[
            TimeseriesPoint(bucket=b.bucket, negative=b.negative, neutral=b.neutral, positive=b.positive)
            for b in timeseries
        ],
        model_versions=[ModelVersionCount(model_version=version, count=count) for version, count in model_versions],
    )
