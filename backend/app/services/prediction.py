"""Single-text prediction: validate -> normalise -> cache lookup -> model -> cache write -> store."""
from __future__ import annotations

import hashlib
import logging
import time
import uuid
from dataclasses import dataclass

from sentiment_ml.inference import Prediction as ModelPrediction
from sentiment_ml.inference import SentimentModel
from sqlalchemy.orm import Session

from app.core.errors import InputValidationError
from app.db import repository
from app.db.models import Prediction
from app.schemas.common import CacheStatus, PredictionSource
from app.services.cache import PredictionCache, cache_key

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PreparedText:
    text: str  # the submitted text, stripped: what we store and echo back
    text_sha256: str  # hash of the normalised text the model sees


def prepare_text(raw_text: str, model: SentimentModel, max_length: int) -> PreparedText:
    """Apply the input rules shared by single and batch predictions.

    Raises InputValidationError with a user-facing message if the text is unusable.
    """
    text = raw_text.strip()
    if not text:
        raise InputValidationError("Text must not be empty.", field="text")
    if len(text) > max_length:
        raise InputValidationError(
            f"Text must be at most {max_length} characters (received {len(text)}).", field="text"
        )
    normalized = model.normalize(text)
    if not normalized:
        # e.g. "... ---": nothing the model could read, so any answer would be meaningless.
        raise InputValidationError("Text has no analysable content.", field="text")
    return PreparedText(text=text, text_sha256=hashlib.sha256(normalized.encode("utf-8")).hexdigest())


def build_row(
    prepared: PreparedText,
    prediction: ModelPrediction,
    *,
    model_version: str,
    cache_status: CacheStatus,
    latency_ms: float,
    source: PredictionSource = PredictionSource.SINGLE,
    batch_id: uuid.UUID | None = None,
) -> Prediction:
    return Prediction(
        text=prepared.text,
        text_sha256=prepared.text_sha256,
        sentiment=prediction.sentiment,
        confidence=prediction.confidence,
        prob_negative=prediction.probabilities["negative"],
        prob_neutral=prediction.probabilities["neutral"],
        prob_positive=prediction.probabilities["positive"],
        top_words=prediction.top_words,
        model_version=model_version,
        cache_status=cache_status,
        source=source,
        batch_id=batch_id,
        latency_ms=latency_ms,
    )


def predict_text(
    raw_text: str, *, model: SentimentModel, cache: PredictionCache, session: Session, max_text_length: int
) -> Prediction:
    started = time.perf_counter()
    prepared = prepare_text(raw_text, model, max_text_length)
    key = cache_key(model.version, prepared.text_sha256)

    cache_status, prediction = cache.lookup(key)
    if prediction is None:
        prediction = model.predict(prepared.text)
        # Written only after the model succeeded, so errors are never cached. On "bypass"
        # Redis is down or disabled, so there is no point trying to write.
        if cache_status == CacheStatus.MISS:
            cache.store(key, prediction)
    latency_ms = round((time.perf_counter() - started) * 1000, 2)

    row = build_row(prepared, prediction, model_version=model.version, cache_status=cache_status, latency_ms=latency_ms)
    repository.save_predictions(session, [row])

    logger.info(
        "Prediction served",
        extra={
            "event": "prediction",
            "cache_status": cache_status,
            "model_version": model.version,
            "sentiment": prediction.sentiment,
            "latency_ms": latency_ms,
            # A hash prefix identifies repeated posts in the logs without logging user text.
            "text_sha256": prepared.text_sha256[:12],
        },
    )
    return row
