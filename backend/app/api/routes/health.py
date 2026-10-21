from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Request, Response, status
from redis import RedisError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.dependencies import CacheDep, DbSession, OptionalModelDep, SettingsDep
from app.schemas.health import DependencyCheck, HealthChecks, HealthResponse, LivenessResponse, ModelCheck
from app.services.cache import PredictionCache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["Health"])


def _check_database(session: Session) -> DependencyCheck:
    started = time.perf_counter()
    try:
        session.execute(select(1))
    except SQLAlchemyError as exc:
        logger.warning("Health check: database down", extra={"event": "health_check", "error": str(exc)})
        # Only the exception type is returned: the message can contain host names.
        return DependencyCheck(status="down", error=type(exc).__name__)
    return DependencyCheck(status="ok", latency_ms=round((time.perf_counter() - started) * 1000, 2))


def _check_redis(cache: PredictionCache) -> DependencyCheck:
    if not cache.enabled:
        return DependencyCheck(status="disabled")
    try:
        latency_ms = cache.ping()
    except RedisError as exc:
        logger.warning("Health check: Redis down", extra={"event": "health_check", "error": str(exc)})
        return DependencyCheck(status="down", error=type(exc).__name__)
    return DependencyCheck(status="ok", latency_ms=latency_ms)


@router.get(
    "",
    response_model=HealthResponse,
    summary="Readiness: model, database and Redis status",
    responses={503: {"model": HealthResponse, "description": "The model or the database is down"}},
)
def health(
    request: Request,
    response: Response,
    model: OptionalModelDep,
    session: DbSession,
    cache: CacheDep,
    settings: SettingsDep,
) -> HealthResponse:
    """`down` (HTTP 503) if the model or database is unavailable: the API cannot serve
    predictions. `degraded` (HTTP 200) if only Redis is down: predictions still work, uncached."""
    checks = HealthChecks(
        model=ModelCheck(status="ok", version=model.version) if model else ModelCheck(status="down", version=None),
        database=_check_database(session),
        redis=_check_redis(cache),
    )
    if checks.model.status == "down" or checks.database.status == "down":
        overall = "down"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif checks.redis.status == "down":
        overall = "degraded"
    else:
        overall = "ok"

    return HealthResponse(
        status=overall,
        version=settings.app_version,
        environment=settings.environment,
        uptime_seconds=round(time.monotonic() - request.app.state.started_at, 1),
        checks=checks,
    )


@router.get("/live", response_model=LivenessResponse, summary="Liveness: the process is up")
def live() -> LivenessResponse:
    """No dependency checks, so a database outage never makes the platform restart the API."""
    return LivenessResponse(status="alive")
