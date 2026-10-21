"""GET /api/analytics/summary: SQL aggregates, distribution, cache counts and time series."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from tests.helpers import assert_error

NOW = datetime(2026, 10, 20, 12, 30, tzinfo=UTC)


def summary(client, **params):
    response = client.get("/api/analytics/summary", params=params)
    assert response.status_code == 200, response.text
    return response.json()


class TestSummaryTotals:
    def test_empty_database_returns_zeros_for_every_label(self, client):
        body = summary(client)

        assert body["total"] == 0
        assert body["unique_texts"] == 0
        assert body["distribution"] == [
            {"sentiment": "negative", "count": 0, "percentage": 0.0},
            {"sentiment": "neutral", "count": 0, "percentage": 0.0},
            {"sentiment": "positive", "count": 0, "percentage": 0.0},
        ]
        assert body["average_confidence"] is None
        assert body["cache"] == {"hit": 0, "miss": 0, "bypass": 0, "hit_rate": None}
        assert body["timeseries"] == []
        assert body["model_versions"] == []

    def test_aggregates_counts_confidence_and_cache(self, client, add_prediction):
        add_prediction(sentiment="negative", confidence=0.9, cache_status="miss", text_sha256="1" * 64)
        add_prediction(sentiment="negative", confidence=0.5, cache_status="hit", text_sha256="1" * 64)
        add_prediction(sentiment="neutral", confidence=0.4, cache_status="hit", text_sha256="2" * 64)
        add_prediction(sentiment="neutral", confidence=0.8, cache_status="bypass", text_sha256="3" * 64,
                       model_version="old@0.9.0+11111111")

        body = summary(client)

        assert body["total"] == 4
        assert body["unique_texts"] == 3
        assert body["distribution"] == [
            {"sentiment": "negative", "count": 2, "percentage": 50.0},
            {"sentiment": "neutral", "count": 2, "percentage": 50.0},
            {"sentiment": "positive", "count": 0, "percentage": 0.0},
        ]
        assert body["average_confidence"] == 0.65
        assert body["low_confidence_count"] == 2  # below the 0.55 threshold
        # Bypassed requests never reached Redis, so the hit rate is 2 hits / 3 lookups.
        assert body["cache"] == {"hit": 2, "miss": 1, "bypass": 1, "hit_rate": 0.6667}
        assert body["model_versions"] == [
            {"model_version": "tiny-test-model@0.0.1+abcdef12", "count": 3},
            {"model_version": "old@0.9.0+11111111", "count": 1},
        ]

    def test_percentages_are_rounded_to_one_decimal(self, client, add_prediction):
        for sentiment in ("negative", "neutral", "positive"):
            add_prediction(sentiment=sentiment)

        percentages = [share["percentage"] for share in summary(client)["distribution"]]

        assert percentages == [33.3, 33.3, 33.3]

    def test_applies_sentiment_and_date_filters(self, client, add_prediction):
        add_prediction(sentiment="positive", created_at=NOW)
        add_prediction(sentiment="negative", created_at=NOW)
        add_prediction(sentiment="positive", created_at=NOW - timedelta(days=10))

        body = summary(client, sentiment="positive", date_from=(NOW - timedelta(days=1)).isoformat())

        assert body["total"] == 1
        assert [share["count"] for share in body["distribution"]] == [0, 0, 1]

    def test_rejects_date_from_after_date_to(self, client):
        response = client.get("/api/analytics/summary", params={"date_from": "2026-10-21", "date_to": "2026-10-20"})

        assert_error(response, 422, "VALIDATION_ERROR", field="date_from")


class TestSummaryTimeseries:
    def test_hourly_buckets_for_a_short_span(self, client, add_prediction):
        add_prediction(sentiment="negative", created_at=NOW.replace(minute=5))
        add_prediction(sentiment="negative", created_at=NOW.replace(minute=50))
        add_prediction(sentiment="positive", created_at=NOW.replace(minute=50))
        add_prediction(sentiment="neutral", created_at=NOW + timedelta(hours=2))

        body = summary(client)

        assert body["granularity"] == "hour"
        assert body["timeseries"] == [
            {"bucket": "2026-10-20T12:00:00Z", "negative": 2, "neutral": 0, "positive": 1},
            {"bucket": "2026-10-20T14:00:00Z", "negative": 0, "neutral": 1, "positive": 0},
        ]

    def test_daily_buckets_when_data_spans_more_than_two_days(self, client, add_prediction):
        add_prediction(sentiment="positive", created_at=NOW - timedelta(days=4))
        add_prediction(sentiment="negative", created_at=NOW)

        body = summary(client)

        assert body["granularity"] == "day"
        assert [point["bucket"] for point in body["timeseries"]] == ["2026-10-16T00:00:00Z", "2026-10-20T00:00:00Z"]

    def test_requested_range_decides_granularity(self, client, add_prediction):
        add_prediction(created_at=NOW)

        short = summary(client, date_from=(NOW - timedelta(days=1)).isoformat(), date_to=NOW.isoformat())
        long = summary(client, date_from=(NOW - timedelta(days=30)).isoformat(), date_to=NOW.isoformat())

        assert (short["granularity"], long["granularity"]) == ("hour", "day")
