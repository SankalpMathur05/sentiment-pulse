"""Redis cache for model predictions, designed to degrade gracefully.

Key:   sentiment:v1:{model_version}:{sha256 of normalised text}
Value: JSON of the model's Prediction (sentiment, confidence, probabilities, top_words)

The model version is part of the key, so a retrained model never reuses predictions made
by an older one. The cache is an optimisation, not a dependency: if Redis is down or slow,
lookups report "bypass", writes are skipped, and predictions still succeed.

After a Redis error the cache "trips" (a simple circuit breaker): for RETRY_AFTER_SECONDS
it doesn't contact Redis at all, so only one request pays the connection timeout instead
of every request. The first call after the pause tries Redis again.
"""
from __future__ import annotations

import dataclasses
import json
import logging
import time

from redis import ConnectionError as RedisConnectionError
from redis import Redis, RedisError
from redis.backoff import NoBackoff
from redis.retry import Retry
from sentiment_ml.inference import Prediction as ModelPrediction

from app.schemas.cache import CacheStatsResponse
from app.schemas.common import CacheStatus

logger = logging.getLogger(__name__)

# Bump "v1" if the format of the cached value ever changes, so old entries are ignored.
KEY_PREFIX = "sentiment:v1"
# Counting keys walks the keyspace with SCAN; stop early so the stats call stays cheap.
MAX_KEYS_COUNTED = 10_000
REDIS_TIMEOUT_SECONDS = 1.0
# How long to stop calling Redis after it fails. Name resolution of a stopped container can
# take several seconds (longer than the socket timeout), so this bounds the damage.
RETRY_AFTER_SECONDS = 30.0

CacheLookup = tuple[CacheStatus, ModelPrediction | None]


def create_redis_client(redis_url: str) -> Redis:
    return Redis.from_url(
        redis_url,
        decode_responses=True,
        # Short timeouts and no retries: a slow cache is worse than no cache. After a failure
        # the request falls back to the model, and the next request reconnects.
        socket_timeout=REDIS_TIMEOUT_SECONDS,
        socket_connect_timeout=REDIS_TIMEOUT_SECONDS,
        retry=Retry(NoBackoff(), retries=0),
    )


def cache_key(model_version: str, text_sha256: str) -> str:
    return f"{KEY_PREFIX}:{model_version}:{text_sha256}"


def _encode(prediction: ModelPrediction) -> str:
    return json.dumps(dataclasses.asdict(prediction))


def _decode(raw: str) -> ModelPrediction:
    return ModelPrediction(**json.loads(raw))


def _log_unavailable(operation: str, exc: RedisError) -> None:
    logger.warning(
        "Redis unavailable, continuing without cache",
        extra={"event": "cache_unavailable", "operation": operation, "error": type(exc).__name__},
    )


class PredictionCache:
    def __init__(self, client: Redis | None, ttl_seconds: int, retry_after_seconds: float = RETRY_AFTER_SECONDS) -> None:
        """`client` is None when caching is disabled (CACHE_ENABLED=false)."""
        self._client = client
        self.ttl_seconds = ttl_seconds
        self._retry_after_seconds = retry_after_seconds
        self._paused_until = 0.0  # time.monotonic() value; Redis is skipped until then

    @property
    def enabled(self) -> bool:
        return self._client is not None

    def _usable(self) -> bool:
        return self._client is not None and time.monotonic() >= self._paused_until

    def _trip(self, operation: str, exc: RedisError) -> None:
        self._paused_until = time.monotonic() + self._retry_after_seconds
        _log_unavailable(operation, exc)

    # --- Lookups -------------------------------------------------------------------------

    def lookup(self, key: str) -> CacheLookup:
        if not self._usable():
            return CacheStatus.BYPASS, None
        try:
            raw = self._client.get(key)
        except RedisError as exc:
            self._trip("get", exc)
            return CacheStatus.BYPASS, None
        if raw is None:
            return CacheStatus.MISS, None
        return CacheStatus.HIT, _decode(raw)

    def lookup_many(self, keys: list[str]) -> list[CacheLookup]:
        """One MGET round trip for a whole batch, instead of one GET per row."""
        if not self._usable() or not keys:
            return [(CacheStatus.BYPASS, None)] * len(keys)
        try:
            raws = self._client.mget(keys)
        except RedisError as exc:
            self._trip("mget", exc)
            return [(CacheStatus.BYPASS, None)] * len(keys)
        return [(CacheStatus.MISS, None) if raw is None else (CacheStatus.HIT, _decode(raw)) for raw in raws]

    # --- Writes (only ever called with successful predictions) ----------------------------

    def store(self, key: str, prediction: ModelPrediction) -> None:
        if not self._usable():
            return
        try:
            # SET with EX is the atomic equivalent of SETEX (redis-py 8 deprecates setex()).
            self._client.set(key, _encode(prediction), ex=self.ttl_seconds)
        except RedisError as exc:
            self._trip("set", exc)

    def store_many(self, items: dict[str, ModelPrediction]) -> None:
        if not self._usable() or not items:
            return
        try:
            # A non-transactional pipeline sends all writes in one round trip.
            with self._client.pipeline(transaction=False) as pipe:
                for key, prediction in items.items():
                    pipe.set(key, _encode(prediction), ex=self.ttl_seconds)
                pipe.execute()
        except RedisError as exc:
            self._trip("pipeline_set", exc)

    # --- Monitoring ----------------------------------------------------------------------

    def ping(self) -> float:
        """Round-trip time in ms. Raises RedisError if Redis is unreachable (or was a moment ago)."""
        if not self._usable():
            raise RedisConnectionError("Redis failed recently; waiting before retrying")
        started = time.perf_counter()
        try:
            self._client.ping()
        except RedisError as exc:
            self._trip("ping", exc)
            raise
        return round((time.perf_counter() - started) * 1000, 2)

    def stats(self) -> CacheStatsResponse:
        """Cache statistics. hits/misses come from Redis INFO and are server-wide, i.e. they
        include every key on the Redis server, not only sentiment predictions."""
        unavailable = CacheStatsResponse(
            enabled=self.enabled, available=False, ttl_seconds=self.ttl_seconds,
            keys=None, hits=None, misses=None, hit_rate=None, used_memory_human=None,
        )
        if not self._usable():
            return unavailable
        try:
            stats = self._client.info("stats")
            memory = self._client.info("memory")
            keys = self._count_prediction_keys()
        except RedisError as exc:
            self._trip("info", exc)
            return unavailable

        hits, misses = stats.get("keyspace_hits", 0), stats.get("keyspace_misses", 0)
        return CacheStatsResponse(
            enabled=True,
            available=True,
            ttl_seconds=self.ttl_seconds,
            keys=keys,
            hits=hits,
            misses=misses,
            hit_rate=round(hits / (hits + misses), 4) if hits + misses else None,
            used_memory_human=memory.get("used_memory_human"),
        )

    def _count_prediction_keys(self) -> int:
        # SCAN (not KEYS) iterates in small steps and never blocks Redis for other clients.
        count = 0
        for _ in self._client.scan_iter(match=f"{KEY_PREFIX}:*", count=1000):
            count += 1
            if count >= MAX_KEYS_COUNTED:
                break
        return count
