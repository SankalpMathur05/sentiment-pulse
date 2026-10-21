"""FastAPI dependencies: how routes get settings, a database session, the cache and the model.

Shared resources are created once in the app lifespan (main.py) and kept on `app.state`;
these functions hand them to routes. Tests replace them with `app.dependency_overrides`.
"""
from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, Query, Request
from sentiment_ml.inference import SentimentModel
from sqlalchemy.orm import Session

from app.config import Settings
from app.core.errors import InputValidationError, ModelUnavailableError
from app.db.repository import PredictionFilters
from app.schemas.common import Sentiment
from app.services.cache import PredictionCache


def get_settings(request: Request) -> Settings:
    """The Settings this app instance was created with (not re-read from the environment)."""
    return request.app.state.settings


def get_db(request: Request) -> Iterator[Session]:
    """One session per request, always closed (and rolled back if not committed) afterwards."""
    with request.app.state.session_factory() as session:
        yield session


def get_cache(request: Request) -> PredictionCache:
    return request.app.state.cache


def get_optional_model(request: Request) -> SentimentModel | None:
    """The loaded model, or None if it failed to load at startup."""
    return request.app.state.model


def get_model(model: Annotated[SentimentModel | None, Depends(get_optional_model)]) -> SentimentModel:
    if model is None:
        raise ModelUnavailableError()
    return model


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    # A timestamp without an offset is taken to be UTC, the timezone everything is stored in.
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def get_prediction_filters(
    sentiment: Annotated[Sentiment | None, Query(description="Only predictions with this label.")] = None,
    date_from: Annotated[
        datetime | None, Query(description="Inclusive lower bound (ISO 8601). No offset means UTC.")
    ] = None,
    date_to: Annotated[
        datetime | None, Query(description="Inclusive upper bound (ISO 8601). No offset means UTC.")
    ] = None,
) -> PredictionFilters:
    date_from, date_to = _as_utc(date_from), _as_utc(date_to)
    if date_from is not None and date_to is not None and date_from > date_to:
        raise InputValidationError("date_from must be earlier than or equal to date_to.", field="date_from")
    return PredictionFilters(sentiment=sentiment, date_from=date_from, date_to=date_to)


SettingsDep = Annotated[Settings, Depends(get_settings)]
DbSession = Annotated[Session, Depends(get_db)]
CacheDep = Annotated[PredictionCache, Depends(get_cache)]
ModelDep = Annotated[SentimentModel, Depends(get_model)]
OptionalModelDep = Annotated[SentimentModel | None, Depends(get_optional_model)]
FiltersDep = Annotated[PredictionFilters, Depends(get_prediction_filters)]
