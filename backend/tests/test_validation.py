"""Input validation and the error envelope shared by every non-2xx response."""
from __future__ import annotations

import pytest

from tests.helpers import assert_error


class TestPredictValidation:
    @pytest.mark.parametrize(
        ("payload", "field", "message"),
        [
            pytest.param({}, "text", "This field is required.", id="missing-field"),
            pytest.param({"text": 123}, "text", "Input should be a valid string.", id="number"),
            pytest.param({"text": None}, "text", "Input should be a valid string.", id="null"),
            pytest.param({"text": ""}, "text", "Text must not be empty.", id="empty"),
            pytest.param({"text": "   \n\t "}, "text", "Text must not be empty.", id="whitespace-only"),
            pytest.param(
                {"text": "a" * 1001}, "text", "Text must be at most 1000 characters (received 1001).", id="too-long"
            ),
            pytest.param(
                {"text": "hello", "lang": "en"}, "lang", "Unknown field; it is not allowed.", id="extra-field"
            ),
            pytest.param(
                {"text": "... --- ,,,"}, "text", "Text has no analysable content.", id="no-analysable-content"
            ),
        ],
    )
    def test_rejects_invalid_body(self, client, payload, field, message):
        response = client.post("/api/predict", json=payload)

        error = assert_error(response, 422, "VALIDATION_ERROR", field=field)
        assert error["details"][0]["message"] == message
        assert error["message"] == message

    def test_rejects_malformed_json(self, client):
        response = client.post(
            "/api/predict", content=b'{"text": "unterminated', headers={"Content-Type": "application/json"}
        )

        error = assert_error(response, 422, "VALIDATION_ERROR")
        assert error["details"] == [{"field": None, "message": "Request body is not valid JSON."}]

    def test_rejects_non_object_body(self, client):
        response = client.post("/api/predict", json=["not", "an", "object"])

        assert_error(response, 422, "VALIDATION_ERROR")

    def test_rejects_missing_body(self, client):
        response = client.post("/api/predict")

        error = assert_error(response, 422, "VALIDATION_ERROR")
        assert error["details"] == [{"field": None, "message": "Request body is required."}]

    def test_length_limit_is_configurable(self, make_client):
        client = make_client(max_text_length=10)

        response = client.post("/api/predict", json={"text": "this is longer than ten"})

        error = assert_error(response, 422, "VALIDATION_ERROR", field="text")
        assert error["message"] == "Text must be at most 10 characters (received 23)."

    def test_invalid_input_is_not_stored(self, client):
        client.post("/api/predict", json={"text": ""})

        assert client.get("/api/predictions").json()["total"] == 0


class TestErrorEnvelope:
    def test_unknown_route_returns_404_envelope(self, client):
        assert_error(client.get("/api/does-not-exist"), 404, "NOT_FOUND")

    def test_wrong_method_returns_405_envelope(self, client):
        response = client.get("/api/predict")

        assert_error(response, 405, "METHOD_NOT_ALLOWED")
        assert response.headers["Allow"] == "POST"

    def test_echoes_incoming_request_id(self, client):
        response = client.post("/api/predict", json={}, headers={"X-Request-ID": "trace-abc.123"})

        assert response.headers["X-Request-ID"] == "trace-abc.123"
        assert response.json()["error"]["request_id"] == "trace-abc.123"

    def test_replaces_malformed_request_id(self, client):
        response = client.get("/health/live", headers={"X-Request-ID": "<script> spaces & symbols"})

        assert response.headers["X-Request-ID"] != "<script> spaces & symbols"
        assert len(response.headers["X-Request-ID"]) == 32
