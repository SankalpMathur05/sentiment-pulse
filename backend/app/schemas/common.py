"""Types shared across the API: enums, the error envelope and prediction building blocks."""
from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class Sentiment(StrEnum):
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    POSITIVE = "positive"


class CacheStatus(StrEnum):
    HIT = "hit"
    MISS = "miss"
    BYPASS = "bypass"  # cache disabled or Redis unavailable: the model was called directly


class PredictionSource(StrEnum):
    SINGLE = "single"
    BATCH = "batch"


class ErrorCode(StrEnum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    BAD_REQUEST = "BAD_REQUEST"
    NOT_FOUND = "NOT_FOUND"
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
    PAYLOAD_TOO_LARGE = "PAYLOAD_TOO_LARGE"
    UNSUPPORTED_MEDIA_TYPE = "UNSUPPORTED_MEDIA_TYPE"
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
    DATABASE_UNAVAILABLE = "DATABASE_UNAVAILABLE"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    HTTP_ERROR = "HTTP_ERROR"


class ErrorDetail(BaseModel):
    field: str | None = Field(description="Dotted path of the offending input, or null if not field-specific.")
    message: str


class ErrorBody(BaseModel):
    code: ErrorCode
    message: str
    details: list[ErrorDetail] = []
    request_id: str = Field(description="Matches the X-Request-ID response header; quote it when reporting issues.")


class ErrorResponse(BaseModel):
    """The single envelope used by every non-2xx response."""

    error: ErrorBody


_ERROR_DESCRIPTIONS = {
    404: "Resource not found",
    413: "Uploaded file is too large",
    415: "Uploaded file is not a CSV",
    422: "Request validation failed",
    503: "A dependency (model or database) is unavailable",
}


def error_responses(*status_codes: int) -> dict[int | str, dict[str, Any]]:
    """OpenAPI `responses=` entries so /docs shows the error envelope for each status."""
    return {code: {"model": ErrorResponse, "description": _ERROR_DESCRIPTIONS[code]} for code in status_codes}


class Probabilities(BaseModel):
    negative: float
    neutral: float
    positive: float


class TopWord(BaseModel):
    token: str = Field(description="Model feature (a word or bigram, possibly a placeholder like <url>).")
    display: str = Field(description="Human-friendly form of the token, e.g. an emoji instead of its name.")
    weight: float = Field(description="How strongly this word pushed the model towards the predicted label.")
