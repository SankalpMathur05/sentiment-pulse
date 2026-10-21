"""POST /api/predict/batch: CSV parsing, limits, per-row errors, caching and storage."""
from __future__ import annotations

from sqlalchemy import select

from app.db.models import Prediction
from tests.conftest import BrokenRedis
from tests.helpers import assert_error

VALID_CSV = (
    "id,Text\n"
    "1,the crew was great thank you\n"
    "2,my flight was delayed and the staff were rude\n"
    "3,\n"
    "4,... --- ,,,\n"
    f"5,{'a' * 1001}\n"
    "6,what time does the flight board\n"
)


def upload(client, content: str | bytes, filename: str = "posts.csv", content_type: str = "text/csv"):
    data = content.encode("utf-8") if isinstance(content, str) else content
    return client.post("/api/predict/batch", files={"file": (filename, data, content_type)})


class TestBatchHappyPath:
    def test_predicts_valid_rows_and_reports_invalid_ones(self, client, model):
        response = upload(client, VALID_CSV)

        assert response.status_code == 200, response.text
        body = response.json()
        assert (body["total_rows"], body["succeeded"], body["failed"]) == (6, 3, 3)
        assert body["model_version"] == model.version
        assert sum(body["summary"].values()) == 3
        assert body["cache"] == {"hit": 0, "miss": 3, "bypass": 0}

        results = body["results"]
        assert [result["row"] for result in results] == [1, 2, 3, 4, 5, 6]
        assert results[0]["sentiment"] == "positive"
        assert results[1]["sentiment"] == "negative"
        assert [result["error"] for result in results[2:5]] == [
            "Text must not be empty.",
            "Text has no analysable content.",
            "Text must be at most 1000 characters (received 1001).",
        ]
        assert all(result["id"] is None and result["sentiment"] is None for result in results[2:5])

    def test_stores_successful_rows_with_shared_batch_id(self, client, db_session):
        body = upload(client, VALID_CSV).json()

        rows = db_session.scalars(select(Prediction)).all()
        assert len(rows) == 3
        assert {row.source for row in rows} == {"batch"}
        assert {str(row.batch_id) for row in rows} == {body["batch_id"]}
        assert {str(row.id) for row in rows} == {result["id"] for result in body["results"] if result["id"]}

    def test_second_upload_is_served_from_cache(self, client):
        upload(client, VALID_CSV)

        body = upload(client, VALID_CSV).json()

        assert body["cache"] == {"hit": 3, "miss": 0, "bypass": 0}

    def test_shares_cache_with_single_predictions(self, client):
        client.post("/api/predict", json={"text": "the crew was great thank you"})

        body = upload(client, "text\nthe crew was great thank you\n").json()

        assert body["results"][0]["cache_status"] == "hit"

    def test_works_when_redis_is_down(self, make_client):
        client = make_client(redis_client=BrokenRedis())

        body = upload(client, VALID_CSV).json()

        assert body["succeeded"] == 3
        assert body["cache"] == {"hit": 0, "miss": 0, "bypass": 3}

    def test_accepts_utf8_bom_and_windows_csv_content_type(self, client):
        content = "﻿text\r\nthe crew was great\r\n".encode()

        response = upload(client, content, content_type="application/vnd.ms-excel")

        assert response.status_code == 200
        assert response.json()["succeeded"] == 1


class TestBatchRejectedFiles:
    def test_missing_text_column(self, client):
        response = upload(client, "message\nhello\n")

        error = assert_error(response, 422, "VALIDATION_ERROR", field="file")
        assert error["message"] == 'The CSV file must have a column named "text".'

    def test_header_without_rows(self, client):
        assert_error(upload(client, "text\n"), 422, "VALIDATION_ERROR", field="file")

    def test_empty_file(self, client):
        assert_error(upload(client, ""), 422, "VALIDATION_ERROR", field="file")

    def test_too_many_rows(self, make_client):
        client = make_client(batch_max_rows=2)

        response = upload(client, "text\none\ntwo\nthree\n")

        error = assert_error(response, 422, "VALIDATION_ERROR", field="file")
        assert error["message"] == "The CSV file has 3 rows; the maximum is 2."

    def test_file_too_large(self, make_client):
        client = make_client(batch_max_bytes=100)

        assert_error(upload(client, "text\n" + "great flight\n" * 20), 413, "PAYLOAD_TOO_LARGE")

    def test_not_a_csv(self, client):
        response = upload(client, '{"text": "hi"}', filename="posts.json", content_type="application/json")

        assert_error(response, 415, "UNSUPPORTED_MEDIA_TYPE")

    def test_not_utf8(self, client):
        response = upload(client, "text\ncaf\xe9 was great\n".encode("latin-1"))

        assert_error(response, 422, "VALIDATION_ERROR", field="file")

    def test_missing_file_field(self, client):
        response = client.post("/api/predict/batch", data={"other": "value"})

        assert_error(response, 422, "VALIDATION_ERROR", field="file")

    def test_rejected_file_stores_nothing(self, client, db_session):
        upload(client, "message\nhello\n")

        assert db_session.scalars(select(Prediction)).all() == []
