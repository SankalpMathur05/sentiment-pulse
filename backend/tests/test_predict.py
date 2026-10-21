"""POST /api/predict happy path, persistence, logging, dependency failures, and GET /api/model."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime

import pytest
from sqlalchemy import select

from app.db.models import Prediction
from tests.helpers import assert_error

POSITIVE_TEXT = "the crew was great, thank you"


class TestPredictHappyPath:
    def test_returns_full_prediction(self, client, model):
        response = client.post("/api/predict", json={"text": POSITIVE_TEXT})

        assert response.status_code == 200
        body = response.json()
        assert set(body) == {
            "id", "text", "sentiment", "confidence", "probabilities", "top_words", "is_low_confidence",
            "model_version", "cache_status", "latency_ms", "created_at",
        }
        uuid.UUID(body["id"])
        assert body["text"] == POSITIVE_TEXT
        assert body["sentiment"] == "positive"
        assert set(body["probabilities"]) == {"negative", "neutral", "positive"}
        assert sum(body["probabilities"].values()) == pytest.approx(1, abs=1e-3)
        assert body["confidence"] == max(body["probabilities"].values())
        assert body["is_low_confidence"] == (body["confidence"] < 0.55)
        assert body["model_version"] == model.version
        assert body["cache_status"] == "miss"
        assert body["latency_ms"] >= 0
        assert all(set(word) == {"token", "display", "weight"} for word in body["top_words"])
        assert datetime.fromisoformat(body["created_at"]).utcoffset().total_seconds() == 0

    def test_sets_cache_and_request_id_headers(self, client):
        response = client.post("/api/predict", json={"text": POSITIVE_TEXT})

        assert response.headers["X-Cache"] == "MISS"
        assert len(response.headers["X-Request-ID"]) == 32

    def test_returns_text_without_surrounding_whitespace(self, client):
        response = client.post("/api/predict", json={"text": f"  \n {POSITIVE_TEXT}\t "})

        assert response.json()["text"] == POSITIVE_TEXT

    def test_accepts_text_at_the_length_limit(self, client):
        response = client.post("/api/predict", json={"text": "a" * 1000})

        assert response.status_code == 200

    def test_low_confidence_flag_uses_configured_threshold(self, make_client):
        client = make_client(low_confidence_threshold=0.99)

        response = client.post("/api/predict", json={"text": POSITIVE_TEXT})

        assert response.json()["is_low_confidence"] is True


class TestPredictPersistence:
    def test_stores_the_prediction(self, client, db_session):
        body = client.post("/api/predict", json={"text": POSITIVE_TEXT}).json()

        row = db_session.scalars(select(Prediction)).one()
        assert str(row.id) == body["id"]
        assert row.text == POSITIVE_TEXT
        assert row.sentiment == body["sentiment"]
        assert row.prob_positive == body["probabilities"]["positive"]
        assert row.cache_status == "miss"
        assert row.source == "single"
        assert row.batch_id is None
        assert len(row.text_sha256) == 64
        assert row.created_at.tzinfo is not None

    def test_logs_one_structured_line_without_the_raw_text(self, client, caplog):
        caplog.set_level(logging.INFO)

        client.post("/api/predict", json={"text": POSITIVE_TEXT})

        [record] = [r for r in caplog.records if getattr(r, "event", None) == "prediction"]
        assert record.cache_status == "miss"
        assert record.sentiment == "positive"
        assert len(record.text_sha256) == 12
        assert all(POSITIVE_TEXT not in str(vars(r)) for r in caplog.records)


class TestPredictDependencyFailures:
    def test_returns_503_when_model_is_not_loaded(self, make_client, tmp_path):
        client = make_client(model_dir=tmp_path / "missing-model")

        response = client.post("/api/predict", json={"text": POSITIVE_TEXT})

        assert_error(response, 503, "MODEL_UNAVAILABLE")

    def test_returns_503_when_database_is_down(self, make_client):
        client = make_client(database_url="postgresql+psycopg://sentiment:sentiment@127.0.0.1:1/none")

        response = client.post("/api/predict", json={"text": POSITIVE_TEXT})

        assert_error(response, 503, "DATABASE_UNAVAILABLE")

    def test_unexpected_error_returns_generic_500(self, client, model, monkeypatch):
        def explode(*args, **kwargs):
            raise RuntimeError("secret internal detail")

        monkeypatch.setattr(model, "predict", explode)

        response = client.post("/api/predict", json={"text": POSITIVE_TEXT})

        error = assert_error(response, 500, "INTERNAL_ERROR")
        assert "secret" not in response.text
        assert error["details"] == []


class TestModelInfo:
    def test_returns_model_card_from_metadata(self, client, model):
        response = client.get("/api/model")

        assert response.status_code == 200
        body = response.json()
        assert body["version"] == model.version
        assert body["name"] == "tiny-test-model"
        assert body["labels"] == ["negative", "neutral", "positive"]
        assert body["low_confidence_threshold"] == 0.55
        assert body["dataset"] == {
            "name": "hand-written airline posts", "homepage": "https://example.com",
            "licence": "CC0-1.0", "rows_train": 30, "rows_test": 0,
        }
        assert body["metrics"]["macro_f1"] == 0.9
        assert body["metrics"]["per_class"]["negative"]["support"] == 10
        assert body["comparison"][0]["selected"] is True
        assert body["top_features"]["positive"][0]["token"] == "great"
        assert body["limitations"]

    def test_returns_503_when_model_is_not_loaded(self, make_client, tmp_path):
        client = make_client(model_dir=tmp_path / "missing-model")

        assert_error(client.get("/api/model"), 503, "MODEL_UNAVAILABLE")
