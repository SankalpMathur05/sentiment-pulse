"""GET /api/predictions (filters, pagination) and GET /api/predictions/{id}."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from tests.helpers import assert_error

NOW = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)


class TestListPredictions:
    def test_lists_newest_first_with_full_records(self, client, add_prediction):
        older = add_prediction(created_at=NOW - timedelta(hours=1))
        newer = add_prediction(created_at=NOW, source="batch", batch_id=uuid.uuid4())

        body = client.get("/api/predictions").json()

        assert [item["id"] for item in body["items"]] == [str(newer.id), str(older.id)]
        assert (body["total"], body["page"], body["page_size"], body["pages"]) == (2, 1, 20, 1)
        item = body["items"][0]
        assert item["source"] == "batch"
        assert item["batch_id"] == str(newer.batch_id)
        assert item["probabilities"] == {"negative": 0.1, "neutral": 0.8, "positive": 0.1}
        assert item["is_low_confidence"] is False

    def test_paginates(self, client, add_prediction):
        rows = [add_prediction(created_at=NOW - timedelta(minutes=i)) for i in range(5)]

        body = client.get("/api/predictions", params={"page": 3, "page_size": 2}).json()

        assert (body["total"], body["pages"]) == (5, 3)
        assert [item["id"] for item in body["items"]] == [str(rows[4].id)]

    def test_page_past_the_end_is_empty(self, client, add_prediction):
        add_prediction()

        body = client.get("/api/predictions", params={"page": 5}).json()

        assert (body["items"], body["total"]) == ([], 1)

    def test_filters_by_sentiment(self, client, add_prediction):
        add_prediction(sentiment="negative")
        positive = add_prediction(sentiment="positive")

        body = client.get("/api/predictions", params={"sentiment": "positive"}).json()

        assert [item["id"] for item in body["items"]] == [str(positive.id)]

    def test_filters_by_inclusive_date_range(self, client, add_prediction):
        add_prediction(created_at=NOW - timedelta(days=3))
        start = add_prediction(created_at=NOW - timedelta(days=2))
        end = add_prediction(created_at=NOW)
        add_prediction(created_at=NOW + timedelta(seconds=1))

        params = {"date_from": (NOW - timedelta(days=2)).isoformat(), "date_to": NOW.isoformat()}
        body = client.get("/api/predictions", params=params).json()

        assert {item["id"] for item in body["items"]} == {str(start.id), str(end.id)}

    def test_treats_datetimes_without_offset_as_utc(self, client, add_prediction):
        inside = add_prediction(created_at=NOW)
        add_prediction(created_at=NOW - timedelta(hours=3))

        # 10:30 in UTC-02:00 is 12:30 UTC; the naive 11:30 bound is read as 11:30 UTC.
        params = {"date_from": "2026-10-20T11:30:00", "date_to": "2026-10-20T10:30:00-02:00"}
        body = client.get("/api/predictions", params=params).json()

        assert [item["id"] for item in body["items"]] == [str(inside.id)]

    def test_rejects_date_from_after_date_to(self, client):
        response = client.get("/api/predictions", params={"date_from": "2026-10-21", "date_to": "2026-10-20"})

        assert_error(response, 422, "VALIDATION_ERROR", field="date_from")

    @pytest.mark.parametrize(
        ("params", "field"),
        [
            ({"sentiment": "angry"}, "sentiment"),
            ({"page": 0}, "page"),
            ({"page_size": 101}, "page_size"),
            ({"date_from": "yesterday"}, "date_from"),
        ],
    )
    def test_rejects_invalid_query_parameters(self, client, params, field):
        assert_error(client.get("/api/predictions", params=params), 422, "VALIDATION_ERROR", field=field)


class TestGetPrediction:
    def test_returns_prediction_created_through_the_api(self, client):
        created = client.post("/api/predict", json={"text": "the crew was great, thank you"}).json()

        response = client.get(f"/api/predictions/{created['id']}")

        assert response.status_code == 200
        record = response.json()
        assert {key: record[key] for key in created} == created
        assert (record["source"], record["batch_id"]) == ("single", None)

    def test_returns_404_for_unknown_id(self, client):
        response = client.get(f"/api/predictions/{uuid.uuid4()}")

        assert_error(response, 404, "NOT_FOUND")

    def test_returns_422_for_malformed_id(self, client):
        assert_error(client.get("/api/predictions/not-a-uuid"), 422, "VALIDATION_ERROR", field="prediction_id")
