"""Redis caching: hits and misses, key design, graceful degradation, and /api/cache/stats."""
from __future__ import annotations

import fakeredis
from redis import ConnectionError as RedisConnectionError
from sentiment_ml.inference import SentimentModel
from sqlalchemy import select

from app.db.models import Prediction
from app.services.cache import PredictionCache
from tests.conftest import BrokenRedis
from tests.helpers import assert_error

TEXT = "my flight was delayed and the staff were rude"


def predict(client, text=TEXT):
    return client.post("/api/predict", json={"text": text})


class TestCacheHitAndMiss:
    def test_second_identical_request_is_served_from_cache(self, client, db_session):
        first = predict(client)
        second = predict(client)

        assert (first.json()["cache_status"], first.headers["X-Cache"]) == ("miss", "MISS")
        assert (second.json()["cache_status"], second.headers["X-Cache"]) == ("hit", "HIT")
        for field in ("sentiment", "confidence", "probabilities", "top_words", "model_version"):
            assert first.json()[field] == second.json()[field]
        # Both requests are stored: the table is an event log, cache hits included.
        assert first.json()["id"] != second.json()["id"]
        statuses = db_session.scalars(select(Prediction.cache_status).order_by(Prediction.created_at)).all()
        assert statuses == ["miss", "hit"]

    def test_texts_that_normalise_identically_share_a_cache_entry(self, client, model):
        original, variant = "The crew was great!", "   the CREW  was GREAT!!!  "
        assert model.normalize(original) == model.normalize(variant)

        predict(client, original)
        response = predict(client, variant)

        assert response.json()["cache_status"] == "hit"
        assert response.json()["text"] == variant.strip()  # the caller's own text is echoed back

    def test_key_includes_model_version_and_has_ttl(self, client, model, fake_redis):
        predict(client)

        [key] = fake_redis.keys("*")
        prefix, version, digest = key.rsplit(":", 2)
        assert (prefix, version, len(digest)) == ("sentiment:v1", model.version, 64)
        assert 0 < fake_redis.ttl(key) <= 86_400

    def test_new_model_version_does_not_reuse_old_predictions(self, client, model):
        predict(client)
        retrained = SentimentModel(model.pipeline, {**model.metadata, "version": "retrained@2.0.0+cafef00d"})
        client.app.state.model = retrained

        response = predict(client)

        assert response.json()["cache_status"] == "miss"
        assert response.json()["model_version"] == "retrained@2.0.0+cafef00d"

    def test_failed_prediction_is_not_cached(self, client, model, fake_redis, db_session, monkeypatch):
        def explode(*args, **kwargs):
            raise RuntimeError("model crashed")

        monkeypatch.setattr(model, "predict", explode)

        assert_error(predict(client), 500, "INTERNAL_ERROR")
        assert fake_redis.keys("sentiment:v1:*") == []
        assert db_session.scalars(select(Prediction)).all() == []


class TestGracefulDegradation:
    def test_prediction_succeeds_with_bypass_when_redis_is_down(self, make_client, db_session):
        client = make_client(redis_client=BrokenRedis())

        response = predict(client)

        assert response.status_code == 200
        assert (response.json()["cache_status"], response.headers["X-Cache"]) == ("bypass", "BYPASS")
        assert db_session.scalars(select(Prediction.cache_status)).all() == ["bypass"]

    def test_failure_pauses_redis_calls_then_retries(self):
        calls = []

        class CountingBrokenRedis(BrokenRedis):
            def get(self, key):
                calls.append(key)
                raise RedisConnectionError("Redis is down")

        paused = PredictionCache(CountingBrokenRedis(), ttl_seconds=60, retry_after_seconds=60)
        assert [paused.lookup("k")[0], paused.lookup("k")[0]] == ["bypass", "bypass"]
        assert len(calls) == 1  # the second lookup didn't wait on Redis at all

        retrying = PredictionCache(CountingBrokenRedis(), ttl_seconds=60, retry_after_seconds=0)
        retrying.lookup("k"), retrying.lookup("k")
        assert len(calls) == 3  # with no pause, every lookup tries Redis again

    def test_disabled_cache_bypasses_redis(self, make_client, fake_redis):
        client = make_client(cache_enabled=False)

        first, second = predict(client), predict(client)

        assert [first.json()["cache_status"], second.json()["cache_status"]] == ["bypass", "bypass"]
        assert fake_redis.keys("*") == []


class FakeRedisWithInfo(fakeredis.FakeRedis):
    """fakeredis does not implement INFO, so return fixed server statistics."""

    def info(self, section=None, *args, **kwargs):
        return {"keyspace_hits": 3, "keyspace_misses": 1, "used_memory_human": "1.05M"}


class TestCacheStats:
    def test_reports_keys_and_server_stats(self, make_client):
        client = make_client(redis_client=FakeRedisWithInfo(decode_responses=True))
        predict(client)
        predict(client, "what time does the flight board")

        response = client.get("/api/cache/stats")

        assert response.status_code == 200
        assert response.json() == {
            "enabled": True, "available": True, "ttl_seconds": 86_400, "keys": 2,
            "hits": 3, "misses": 1, "hit_rate": 0.75, "used_memory_human": "1.05M",
        }

    def test_reports_unavailable_instead_of_failing_when_redis_is_down(self, make_client):
        client = make_client(redis_client=BrokenRedis())

        response = client.get("/api/cache/stats")

        assert response.status_code == 200
        assert response.json()["enabled"] is True
        assert response.json()["available"] is False
        assert response.json()["keys"] is None

    def test_reports_disabled_cache(self, make_client):
        client = make_client(cache_enabled=False)

        body = client.get("/api/cache/stats").json()

        assert (body["enabled"], body["available"]) == (False, False)
