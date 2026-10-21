"""GET /health (readiness, with dependency checks) and GET /health/live (liveness)."""
from __future__ import annotations

from tests.conftest import BrokenRedis

DOWN_DATABASE_URL = "postgresql+psycopg://sentiment:sentiment@127.0.0.1:1/none"


def test_liveness_does_not_check_dependencies(make_client, tmp_path):
    client = make_client(model_dir=tmp_path / "missing-model", redis_client=BrokenRedis())

    response = client.get("/health/live")

    assert (response.status_code, response.json()) == (200, {"status": "alive"})


def test_ok_when_everything_is_up(client, model):
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert (body["version"], body["environment"]) == ("1.0.0", "development")
    assert body["uptime_seconds"] >= 0
    assert body["checks"]["model"] == {"status": "ok", "version": model.version}
    assert body["checks"]["database"]["status"] == "ok"
    assert body["checks"]["database"]["latency_ms"] >= 0
    assert body["checks"]["redis"]["status"] == "ok"


def test_degraded_but_200_when_only_redis_is_down(make_client):
    client = make_client(redis_client=BrokenRedis())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["checks"]["redis"] == {"status": "down", "latency_ms": None, "error": "ConnectionError"}


def test_redis_reported_as_disabled_when_cache_is_off(make_client):
    body = make_client(cache_enabled=False).get("/health").json()

    assert body["status"] == "ok"
    assert body["checks"]["redis"]["status"] == "disabled"


def test_down_with_503_when_model_is_missing(make_client, tmp_path):
    client = make_client(model_dir=tmp_path / "missing-model")

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json()["status"] == "down"
    assert response.json()["checks"]["model"] == {"status": "down", "version": None}


def test_down_with_503_when_database_is_unreachable(make_client):
    client = make_client(database_url=DOWN_DATABASE_URL)

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json()["status"] == "down"
    database = response.json()["checks"]["database"]
    assert (database["status"], database["error"]) == ("down", "OperationalError")
