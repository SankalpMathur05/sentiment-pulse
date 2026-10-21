"""Per-request context: a request id for tracing and one structured access-log line."""
from __future__ import annotations

import logging
import re
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import request_id_var

logger = logging.getLogger("app.access")

REQUEST_ID_HEADER = "X-Request-ID"
# Only accept well-formed incoming ids so clients cannot inject arbitrary text into our logs.
_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,128}$")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        incoming = request.headers.get(REQUEST_ID_HEADER, "")
        request_id = incoming if _VALID_REQUEST_ID.match(incoming) else uuid.uuid4().hex
        # Each request runs in its own task with its own copy of the context, so this value
        # never leaks into other requests. It is deliberately not reset afterwards, so the
        # outermost 500 handler can still include it in its response.
        request_id_var.set(request_id)

        started = time.perf_counter()
        status_code = 500  # reported if the endpoint raises an unhandled exception
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers[REQUEST_ID_HEADER] = request_id
            return response
        finally:
            logger.info(
                "Request handled",
                extra={
                    "event": "request",
                    "method": request.method,
                    "path": request.url.path,
                    "status": status_code,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                },
            )
