"""Application factory. Run with: uvicorn app.main:app"""
from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sentiment_ml.inference import SentimentModel

from app.api import api_router, health_router
from app.config import Settings, get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import REQUEST_ID_HEADER, RequestContextMiddleware
from app.db.session import create_db_engine, create_session_factory
from app.schemas.common import Sentiment
from app.services.cache import PredictionCache, create_redis_client

logger = logging.getLogger(__name__)

OPENAPI_TAGS = [
    {"name": "Predictions", "description": "Classify posts, one at a time or from a CSV file."},
    {"name": "History", "description": "Browse stored predictions."},
    {"name": "Analytics", "description": "Aggregates for the dashboard."},
    {"name": "Cache", "description": "Redis prediction cache."},
    {"name": "Model", "description": "Information about the deployed model."},
    {"name": "Health", "description": "Liveness and readiness probes."},
]


def load_model(model_dir: Path) -> SentimentModel | None:
    """Load the model once at startup. On failure, log and return None so the API still
    starts: /health reports the model as down and prediction endpoints return 503."""
    try:
        model = SentimentModel.load(model_dir)
    except Exception:  # any failure (missing file, bad checksum, unpickling error) means "no model"
        logger.exception("Model failed to load", extra={"event": "model_load_failed", "model_dir": str(model_dir)})
        return None
    # The database stores one probability column per label, so the label set must match.
    if set(model.labels) != set(Sentiment):
        logger.error("Model labels do not match the API", extra={"event": "model_load_failed", "labels": model.labels})
        return None
    logger.info("Model loaded", extra={"event": "model_loaded", "model_version": model.version})
    return model


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    app.state.started_at = time.monotonic()
    app.state.model = load_model(settings.model_dir)

    # Neither of these connects yet: an unavailable database or Redis must not stop startup.
    engine = create_db_engine(settings.database_url)
    app.state.session_factory = create_session_factory(engine)
    redis_client = create_redis_client(settings.redis_url) if settings.cache_enabled else None
    app.state.cache = PredictionCache(redis_client, settings.cache_ttl_seconds)

    yield

    engine.dispose()
    if redis_client is not None:
        redis_client.close()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="Sentiment Pulse API",
        version=settings.app_version,
        description="Sentiment analysis for social media posts: predictions, history, analytics and model info.",
        openapi_tags=OPENAPI_TAGS,
        lifespan=lifespan,
    )
    app.state.settings = settings

    # Added last = outermost, so every request (including CORS preflights) gets an id and a log line.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
        expose_headers=[REQUEST_ID_HEADER, "X-Cache"],  # let the browser app read them
    )
    app.add_middleware(RequestContextMiddleware)
    register_exception_handlers(app)

    app.include_router(api_router)
    app.include_router(health_router)
    return app


app = create_app()
