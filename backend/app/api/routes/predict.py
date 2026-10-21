from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, Response, UploadFile

from app.dependencies import CacheDep, DbSession, ModelDep, SettingsDep
from app.schemas.common import error_responses
from app.schemas.predict import BatchResponse, PredictRequest, PredictResponse
from app.services import batch as batch_service
from app.services import prediction as prediction_service

router = APIRouter(tags=["Predictions"])


@router.post(
    "/predict",
    response_model=PredictResponse,
    summary="Predict the sentiment of one post",
    response_description="The prediction. The X-Cache header (HIT, MISS or BYPASS) shows whether Redis answered.",
    responses=error_responses(422, 503),
)
def predict(
    payload: PredictRequest,
    response: Response,
    model: ModelDep,
    cache: CacheDep,
    session: DbSession,
    settings: SettingsDep,
) -> PredictResponse:
    """Classify a post as negative, neutral or positive, with probabilities and the words
    that drove the decision. Identical posts (after normalisation) are served from the cache.
    Every request is stored, including cache hits."""
    row = prediction_service.predict_text(
        payload.text, model=model, cache=cache, session=session, max_text_length=settings.max_text_length
    )
    response.headers["X-Cache"] = row.cache_status.upper()
    return PredictResponse.from_row(row, settings.low_confidence_threshold)


@router.post(
    "/predict/batch",
    response_model=BatchResponse,
    summary="Predict the sentiment of every row in a CSV file",
    responses=error_responses(413, 415, 422, 503),
)
def predict_batch(
    file: Annotated[UploadFile, File(description='UTF-8 CSV file with a "text" column (header is case-insensitive).')],
    model: ModelDep,
    cache: CacheDep,
    session: DbSession,
    settings: SettingsDep,
) -> BatchResponse:
    """Upload up to BATCH_MAX_ROWS rows (default 500) and BATCH_MAX_BYTES (default 1 MB).
    Invalid rows are reported individually in `results` and do not fail the upload."""
    texts = batch_service.read_csv_texts(file, max_bytes=settings.batch_max_bytes, max_rows=settings.batch_max_rows)
    return batch_service.predict_batch(
        texts, model=model, cache=cache, session=session, max_text_length=settings.max_text_length
    )
