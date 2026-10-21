"""Structured JSON logging using only the standard library.

Each log line is one JSON object, which log platforms (Render, Docker, Loki...) can
search and filter by field. Fields passed with `extra={...}` become top-level keys, and
the current request id is added automatically so every line of a request can be found.
"""
from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime

# Set by RequestContextMiddleware for the duration of a request.
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

# Attributes every LogRecord has; anything else on a record came from `extra=`.
# ("color_message" is an ANSI-coloured duplicate of the message that uvicorn adds.)
_STANDARD_ATTRS = set(vars(logging.LogRecord("", 0, "", 0, "", None, None))) | {"message", "asctime", "color_message"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_id = request_id_var.get()
        if request_id:
            payload["request_id"] = request_id
        payload.update({key: value for key, value in vars(record).items() if key not in _STANDARD_ATTRS})
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str) -> None:
    root = logging.getLogger()
    root.setLevel(level)
    # Idempotent: create_app() can run several times in one process (the test suite does).
    if not any(isinstance(handler.formatter, JsonFormatter) for handler in root.handlers):
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        root.addHandler(handler)
    # Send uvicorn's own messages through the same JSON handler instead of its plain-text one.
    for name in ("uvicorn", "uvicorn.error"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.propagate = True
    # RequestContextMiddleware already writes one access line per request (with the request id).
    logging.getLogger("uvicorn.access").disabled = True
