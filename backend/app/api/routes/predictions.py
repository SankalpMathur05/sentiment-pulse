from __future__ import annotations

import math
import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from app.core.errors import NotFoundError
from app.db import repository
from app.dependencies import DbSession, FiltersDep, SettingsDep
from app.schemas.common import error_responses
from app.schemas.predictions import PredictionPage, PredictionRecord

router = APIRouter(prefix="/predictions", tags=["History"])


@router.get(
    "",
    response_model=PredictionPage,
    summary="List stored predictions, newest first",
    responses=error_responses(422),
)
def list_predictions(
    filters: FiltersDep,
    session: DbSession,
    settings: SettingsDep,
    page: Annotated[int, Query(ge=1, description="1-based page number.")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page.")] = 20,
) -> PredictionPage:
    rows, total = repository.list_predictions(session, filters, page, page_size)
    return PredictionPage(
        items=[PredictionRecord.from_row(row, settings.low_confidence_threshold) for row in rows],
        page=page,
        page_size=page_size,
        total=total,
        pages=math.ceil(total / page_size),
    )


@router.get(
    "/{prediction_id}",
    response_model=PredictionRecord,
    summary="Get one stored prediction",
    responses=error_responses(404, 422),
)
def get_prediction(prediction_id: uuid.UUID, session: DbSession, settings: SettingsDep) -> PredictionRecord:
    row = repository.get_prediction(session, prediction_id)
    if row is None:
        raise NotFoundError(f"Prediction {prediction_id} was not found.")
    return PredictionRecord.from_row(row, settings.low_confidence_threshold)
