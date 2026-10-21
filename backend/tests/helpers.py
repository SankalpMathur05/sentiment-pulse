"""Assertion helpers shared by the test modules."""
from __future__ import annotations

from typing import Any

from httpx import Response


def assert_error(response: Response, status_code: int, code: str, field: str | None = None) -> dict[str, Any]:
    """Check the standard error envelope and return its `error` object."""
    assert response.status_code == status_code, response.text
    body = response.json()
    assert set(body) == {"error"}
    error = body["error"]
    assert set(error) == {"code", "message", "details", "request_id"}
    assert error["code"] == code
    assert error["message"]
    assert error["request_id"] == response.headers["X-Request-ID"]
    if field is not None:
        assert [detail["field"] for detail in error["details"]] == [field]
    return error
