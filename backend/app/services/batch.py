"""Batch prediction from an uploaded CSV file.

Invalid rows (empty, too long, nothing analysable) are reported per row instead of failing
the whole upload. Valid rows go through the same cache and model as single predictions,
but with one MGET, one model call and one INSERT for the whole batch.
"""
from __future__ import annotations

import csv
import io
import logging
import time
import uuid
from collections import Counter

from fastapi import UploadFile
from sentiment_ml.inference import SentimentModel
from sqlalchemy.orm import Session

from app.core.errors import InputValidationError, PayloadTooLargeError, UnsupportedMediaTypeError
from app.db import repository
from app.schemas.common import CacheStatus, PredictionSource
from app.schemas.predict import BatchResponse, BatchRowResult, CacheCounts, SentimentCounts
from app.services.cache import PredictionCache, cache_key
from app.services.prediction import PreparedText, build_row, prepare_text

logger = logging.getLogger(__name__)

CSV_CONTENT_TYPES = {"text/csv", "application/csv"}


def read_csv_texts(upload: UploadFile, *, max_bytes: int, max_rows: int) -> list[str]:
    """Return the `text` column of an uploaded CSV, enforcing type, size and row limits."""
    filename = (upload.filename or "").lower()
    # Browsers are inconsistent about CSV content types (Windows often sends
    # application/vnd.ms-excel), so a .csv extension is accepted on its own.
    if not (filename.endswith(".csv") or upload.content_type in CSV_CONTENT_TYPES):
        raise UnsupportedMediaTypeError("Upload a CSV file (.csv).")

    # Read one byte past the limit: enough to detect an oversized file without reading all of it.
    content = upload.file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise PayloadTooLargeError(f"The file is larger than the {max_bytes:,}-byte limit.")

    try:
        decoded = content.decode("utf-8-sig")  # "-sig" drops the byte-order mark Excel adds
        rows = [row for row in csv.reader(io.StringIO(decoded)) if row]  # skip blank lines
    except UnicodeDecodeError:
        raise InputValidationError("The file must be UTF-8 encoded.", field="file") from None
    except csv.Error as exc:
        raise InputValidationError(f"The file is not valid CSV ({exc}).", field="file") from None

    if not rows:
        raise InputValidationError("The CSV file is empty.", field="file")
    header, *data = rows
    text_column = next((i for i, name in enumerate(header) if name.strip().lower() == "text"), None)
    if text_column is None:
        raise InputValidationError('The CSV file must have a column named "text".', field="file")
    if not data:
        raise InputValidationError("The CSV file has no data rows.", field="file")
    if len(data) > max_rows:
        raise InputValidationError(f"The CSV file has {len(data)} rows; the maximum is {max_rows}.", field="file")

    # A short row (fewer cells than the header) has no text; it is reported as empty.
    return [row[text_column] if text_column < len(row) else "" for row in data]


def predict_batch(
    texts: list[str], *, model: SentimentModel, cache: PredictionCache, session: Session, max_text_length: int
) -> BatchResponse:
    started = time.perf_counter()
    batch_id = uuid.uuid4()
    results: dict[int, BatchRowResult] = {}

    # 1. Validate every row; invalid ones become row errors.
    valid: list[tuple[int, PreparedText]] = []
    for row_number, raw_text in enumerate(texts, start=1):
        try:
            valid.append((row_number, prepare_text(raw_text, model, max_text_length)))
        except InputValidationError as exc:
            results[row_number] = BatchRowResult(row=row_number, text=raw_text.strip(), error=exc.message)

    # 2. One cache round trip, then one model call for everything the cache did not have.
    keys = [cache_key(model.version, prepared.text_sha256) for _, prepared in valid]
    lookups = cache.lookup_many(keys)
    statuses = [status for status, _ in lookups]
    predictions = [prediction for _, prediction in lookups]
    to_predict = [i for i, prediction in enumerate(predictions) if prediction is None]
    if to_predict:
        fresh = model.predict_many([valid[i][1].text for i in to_predict])
        for i, prediction in zip(to_predict, fresh, strict=True):
            predictions[i] = prediction
        cache.store_many({keys[i]: predictions[i] for i in to_predict if statuses[i] == CacheStatus.MISS})

    # 3. Store all rows in one transaction. Latency is the batch time shared across its rows.
    elapsed_ms = (time.perf_counter() - started) * 1000
    latency_ms = round(elapsed_ms / len(valid), 2) if valid else 0.0
    rows = [
        build_row(
            prepared, prediction, model_version=model.version, cache_status=status, latency_ms=latency_ms,
            source=PredictionSource.BATCH, batch_id=batch_id,
        )
        for (_, prepared), prediction, status in zip(valid, predictions, statuses, strict=True)
    ]
    if rows:
        repository.save_predictions(session, rows)

    for (row_number, prepared), row in zip(valid, rows, strict=True):
        results[row_number] = BatchRowResult(
            row=row_number, text=prepared.text, sentiment=row.sentiment,
            confidence=row.confidence, cache_status=row.cache_status, id=row.id,
        )

    sentiment_counts = Counter(row.sentiment for row in rows)
    cache_counts = Counter(statuses)
    logger.info(
        "Batch prediction served",
        extra={
            "event": "batch_prediction",
            "batch_id": str(batch_id),
            "total_rows": len(texts),
            "succeeded": len(rows),
            "cache_hits": cache_counts[CacheStatus.HIT],
            "model_version": model.version,
            "duration_ms": round(elapsed_ms, 2),
        },
    )
    return BatchResponse(
        batch_id=batch_id,
        total_rows=len(texts),
        succeeded=len(rows),
        failed=len(texts) - len(rows),
        summary=SentimentCounts(
            negative=sentiment_counts["negative"],
            neutral=sentiment_counts["neutral"],
            positive=sentiment_counts["positive"],
        ),
        cache=CacheCounts(
            hit=cache_counts[CacheStatus.HIT],
            miss=cache_counts[CacheStatus.MISS],
            bypass=cache_counts[CacheStatus.BYPASS],
        ),
        model_version=model.version,
        results=[results[row_number] for row_number in sorted(results)],
    )
