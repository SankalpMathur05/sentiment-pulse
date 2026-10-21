"""Application errors and the exception handlers that turn every failure into one envelope.

Whatever goes wrong, clients get the same JSON shape (see schemas.common.ErrorResponse)
plus the request id, so the frontend needs a single error-handling path.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError
from starlette import status
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import request_id_var
from app.schemas.common import ErrorBody, ErrorCode, ErrorDetail, ErrorResponse

logger = logging.getLogger(__name__)


class AppError(Exception):
    """An expected failure with a known status code and error code."""

    def __init__(
        self, status_code: int, code: ErrorCode, message: str, details: list[ErrorDetail] | None = None
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or []


class InputValidationError(AppError):
    """Invalid input detected by our own rules (beyond what the Pydantic schema checks)."""

    def __init__(self, message: str, field: str | None = None) -> None:
        super().__init__(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            ErrorCode.VALIDATION_ERROR,
            message,
            [ErrorDetail(field=field, message=message)],
        )


class NotFoundError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(status.HTTP_404_NOT_FOUND, ErrorCode.NOT_FOUND, message)


class PayloadTooLargeError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(status.HTTP_413_CONTENT_TOO_LARGE, ErrorCode.PAYLOAD_TOO_LARGE, message)


class UnsupportedMediaTypeError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, ErrorCode.UNSUPPORTED_MEDIA_TYPE, message)


class ModelUnavailableError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            ErrorCode.MODEL_UNAVAILABLE,
            "The sentiment model is not loaded. See /health for details.",
        )


def error_response(
    status_code: int,
    code: ErrorCode,
    message: str,
    details: list[ErrorDetail] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    request_id = request_id_var.get() or ""
    body = ErrorResponse(error=ErrorBody(code=code, message=message, details=details or [], request_id=request_id))
    # Set the header here too: 500 responses are produced outside the request-id middleware.
    return JSONResponse(
        status_code=status_code,
        content=body.model_dump(mode="json"),
        headers={**(headers or {}), "X-Request-ID": request_id},
    )


# --- Request validation (Pydantic) -------------------------------------------------------

_LOCATION_PREFIXES = {"body", "query", "path", "header", "cookie"}


def _validation_detail(error: dict[str, Any]) -> ErrorDetail:
    error_type = error["type"]
    location = [str(part) for part in error["loc"] if part not in _LOCATION_PREFIXES]
    field = ".".join(location) or None

    if error_type == "json_invalid":
        # The location is a character offset, which is not a field.
        return ErrorDetail(field=None, message="Request body is not valid JSON.")
    if error_type == "missing":
        return ErrorDetail(field=field, message="This field is required." if field else "Request body is required.")
    if error_type == "extra_forbidden":
        return ErrorDetail(field=field, message="Unknown field; it is not allowed.")
    if error_type == "value_error":
        # Our own validators raise ValueError; show their message without Pydantic's "Value error, " prefix.
        return ErrorDetail(field=field, message=str(error["ctx"]["error"]))
    message = error["msg"]
    return ErrorDetail(field=field, message=message if message.endswith(".") else f"{message}.")


async def _handle_request_validation(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = [_validation_detail(error) for error in exc.errors()]
    message = details[0].message if len(details) == 1 else "The request contains invalid fields."
    return error_response(status.HTTP_422_UNPROCESSABLE_CONTENT, ErrorCode.VALIDATION_ERROR, message, details)


# --- Everything else ---------------------------------------------------------------------

_HTTP_ERROR_CODES = {
    400: (ErrorCode.BAD_REQUEST, "The request could not be processed."),
    404: (ErrorCode.NOT_FOUND, "The requested resource was not found."),
    405: (ErrorCode.METHOD_NOT_ALLOWED, "This HTTP method is not allowed for this endpoint."),
    413: (ErrorCode.PAYLOAD_TOO_LARGE, "The request body is too large."),
    415: (ErrorCode.UNSUPPORTED_MEDIA_TYPE, "Unsupported media type."),
}


async def _handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    return error_response(exc.status_code, exc.code, exc.message, exc.details)


async def _handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Errors raised by the framework itself, e.g. unknown routes (404) or wrong methods (405)."""
    code, message = _HTTP_ERROR_CODES.get(exc.status_code, (ErrorCode.HTTP_ERROR, str(exc.detail)))
    # Keep framework headers such as `Allow` on 405 responses.
    return error_response(exc.status_code, code, message, headers=exc.headers)


async def _handle_database_unavailable(request: Request, exc: OperationalError) -> JSONResponse:
    logger.error("Database unavailable", extra={"event": "database_error", "error": type(exc.orig).__name__})
    return error_response(
        status.HTTP_503_SERVICE_UNAVAILABLE,
        ErrorCode.DATABASE_UNAVAILABLE,
        "The database is unavailable. Please try again shortly.",
    )


async def _handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
    # Full stack trace goes to the logs; the client only sees a generic message.
    logger.exception("Unhandled error", extra={"event": "unhandled_error", "path": request.url.path})
    return error_response(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        ErrorCode.INTERNAL_ERROR,
        "An unexpected error occurred. Please try again later.",
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _handle_app_error)
    app.add_exception_handler(RequestValidationError, _handle_request_validation)
    app.add_exception_handler(StarletteHTTPException, _handle_http_exception)
    app.add_exception_handler(OperationalError, _handle_database_unavailable)
    app.add_exception_handler(Exception, _handle_unexpected)
