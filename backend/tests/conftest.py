"""Shared fixtures: a tiny trained model, a migrated Postgres test database, fake Redis
and a factory for API clients with custom settings.

Requires a Postgres server at TEST_DATABASE_URL, e.g.:
  docker run -d --name sp-test-db -e POSTGRES_USER=sentiment -e POSTGRES_PASSWORD=sentiment \
    -e POSTGRES_DB=sentiment_test -p 5433:5432 postgres:16-alpine
"""
from __future__ import annotations

import os
import platform
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import fakeredis
import pytest
import sklearn
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from redis import ConnectionError as RedisConnectionError
from redis import Redis
from sentiment_ml.artifacts import save_model
from sentiment_ml.inference import SentimentModel
from sentiment_ml.preprocessing import PREPROCESSING_VERSION, TextCleaner, tokenize
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sqlalchemy import Engine, create_engine, delete
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.config import Settings
from app.db.models import Prediction
from app.dependencies import get_cache
from app.main import create_app
from app.services.cache import PredictionCache

BACKEND_DIR = Path(__file__).resolve().parents[1]
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://sentiment:sentiment@localhost:5433/sentiment_test"
)

TRAINING_DATA = [
    ("my flight was delayed again, terrible service", "negative"),
    ("lost my luggage and nobody helps, awful", "negative"),
    ("worst airline ever, cancelled flight and rude staff", "negative"),
    ("stuck on the tarmac for three hours, so angry", "negative"),
    ("the seats are broken and the food was disgusting", "negative"),
    ("customer service hung up on me, horrible experience", "negative"),
    ("delayed again, never flying with you again", "negative"),
    ("rude gate agent and a dirty plane", "negative"),
    ("my bag is lost and the refund never came", "negative"),
    ("cancelled without notice, terrible", "negative"),
    ("what time does the flight to boston board", "neutral"),
    ("is there wifi on the flight to denver", "neutral"),
    ("how many bags can i check on a domestic flight", "neutral"),
    ("flight 123 departs from gate 12 today", "neutral"),
    ("can i change my seat online", "neutral"),
    ("what is the baggage allowance for international flights", "neutral"),
    ("does the lounge open at 6am", "neutral"),
    ("i am flying to chicago tomorrow", "neutral"),
    ("please send me the new schedule", "neutral"),
    ("which terminal is the airline in", "neutral"),
    ("thank you for the amazing service, great crew", "positive"),
    ("loved the flight, friendly staff and comfy seats", "positive"),
    ("best airline ever, on time and smooth landing", "positive"),
    ("great job on the quick refund, thanks so much", "positive"),
    ("the crew was wonderful and helpful", "positive"),
    ("awesome upgrade, i love this airline", "positive"),
    ("excellent customer service, very happy", "positive"),
    ("smooth flight and great food, thank you", "positive"),
    ("fantastic experience, will fly again", "positive"),
    ("the pilot was great and we arrived early, love it", "positive"),
]

LABELS = ["negative", "neutral", "positive"]

TINY_MODEL_METADATA: dict[str, Any] = {
    "name": "tiny-test-model",
    "semver": "0.0.1",
    "trained_at": "2026-01-01T00:00:00+00:00",
    "python_version": platform.python_version(),
    "sklearn_version": sklearn.__version__,
    "preprocessing_version": PREPROCESSING_VERSION,
    "random_state": 42,
    "labels": LABELS,
    "cleaning_config": {},
    "hyperparameters": {"C": 1.0},
    "dataset": {
        "name": "hand-written airline posts",
        "url": "https://example.com/tiny.csv",
        "homepage": "https://example.com",
        "licence": "CC0-1.0",
        "sha256": "0" * 64,
        "rows_raw": 30,
        "rows_after_cleaning": 30,
        "rows_train": 30,
        "rows_test": 0,
        "cleaning_report": {},
        "label_distribution_train": {label: 10 for label in LABELS},
    },
    "metrics": {
        "accuracy": 0.9,
        "macro_precision": 0.9,
        "macro_recall": 0.9,
        "macro_f1": 0.9,
        "weighted_f1": 0.9,
        "per_class": {label: {"precision": 0.9, "recall": 0.9, "f1": 0.9, "support": 10} for label in LABELS},
        "confusion_matrix": [[9, 1, 0], [1, 8, 1], [0, 1, 9]],
        "confusion_labels": LABELS,
        "log_loss": 0.3,
        "brier_score": 0.1,
    },
    "comparison": [
        {"model": "tfidf-logreg", "cv_macro_f1": 0.9, "cv_macro_f1_std": 0.01,
         "test_macro_f1": 0.9, "test_accuracy": 0.9, "selected": True},
    ],
    "top_features": {
        "negative": [{"token": "delayed", "display": "delayed", "weight": 1.2}],
        "neutral": [{"token": "what", "display": "what", "weight": 0.8}],
        "positive": [{"token": "great", "display": "great", "weight": 1.5}],
    },
    "limitations": ["Trained on 30 hand-written examples; for tests only."],
}


class BrokenRedis:
    """Stands in for a Redis server that is down: every command raises ConnectionError."""

    def __getattr__(self, name: str) -> Callable[..., Any]:
        def fail(*args: Any, **kwargs: Any) -> Any:
            raise RedisConnectionError("Redis is down")

        return fail


# --- Model ---------------------------------------------------------------------------------

@pytest.fixture(scope="session")
def model_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Train the real pipeline (same steps as production) on 30 examples and save it as an artifact."""
    pipeline = Pipeline([
        ("clean", TextCleaner()),
        ("tfidf", TfidfVectorizer(tokenizer=tokenize, token_pattern=None, lowercase=False, ngram_range=(1, 2))),
        ("clf", LogisticRegression(max_iter=1000, random_state=42)),
    ])
    texts, labels = zip(*TRAINING_DATA, strict=True)
    pipeline.fit(list(texts), list(labels))
    out_dir = tmp_path_factory.mktemp("model")
    save_model(pipeline, TINY_MODEL_METADATA, out_dir)
    return out_dir


# --- Database ------------------------------------------------------------------------------

@pytest.fixture(scope="session")
def db_engine() -> Iterator[Engine]:
    """Build the schema with the real Alembic migrations (down then up, so both are tested)."""
    engine = create_engine(TEST_DATABASE_URL)
    try:
        engine.connect().close()
    except OperationalError:
        pytest.exit(f"Test database not reachable at {TEST_DATABASE_URL} (see tests/conftest.py).", returncode=1)

    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", TEST_DATABASE_URL.replace("%", "%%"))
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine: Engine) -> Iterator[Session]:
    """A session for arranging and checking data. Every test starts with an empty table."""
    with Session(db_engine, expire_on_commit=False) as session:
        session.execute(delete(Prediction))
        session.commit()
        yield session


@pytest.fixture
def add_prediction(db_session: Session) -> Callable[..., Prediction]:
    """Insert a prediction row directly, overriding any column (e.g. created_at)."""

    def _add(**overrides: Any) -> Prediction:
        values: dict[str, Any] = {
            "text": "a stored post",
            "text_sha256": "a" * 64,
            "sentiment": "neutral",
            "confidence": 0.8,
            "prob_negative": 0.1,
            "prob_neutral": 0.8,
            "prob_positive": 0.1,
            "top_words": [],
            "model_version": "tiny-test-model@0.0.1+abcdef12",
            "cache_status": "miss",
            "latency_ms": 1.5,
        }
        row = Prediction(**(values | overrides))
        db_session.add(row)
        db_session.commit()
        return row

    return _add


# --- Application ---------------------------------------------------------------------------

@pytest.fixture
def settings(model_dir: Path) -> Settings:
    # _env_file=None: ignore any developer .env file so tests are reproducible.
    return Settings(
        _env_file=None,
        database_url=TEST_DATABASE_URL,
        redis_url="redis://localhost:6399/0",  # never used: tests inject a fake Redis
        model_dir=model_dir,
    )


@pytest.fixture
def fake_redis() -> Redis:
    return fakeredis.FakeRedis(decode_responses=True)


@pytest.fixture
def make_client(settings: Settings, fake_redis: Redis, db_session: Session) -> Iterator[Callable[..., TestClient]]:
    """Build a started app with optional setting overrides and Redis client.

    Example: make_client(redis_client=BrokenRedis(), batch_max_rows=3)
    """
    clients: list[TestClient] = []

    def _make(redis_client: Any = fake_redis, **setting_overrides: Any) -> TestClient:
        app_settings = settings.model_copy(update=setting_overrides)
        app = create_app(app_settings)
        cache = PredictionCache(redis_client if app_settings.cache_enabled else None, app_settings.cache_ttl_seconds)
        app.dependency_overrides[get_cache] = lambda: cache
        # raise_server_exceptions=False: return the 500 response like a real server would.
        client = TestClient(app, raise_server_exceptions=False)
        client.__enter__()  # runs the lifespan (loads the model)
        clients.append(client)
        return client

    yield _make
    for client in clients:
        client.__exit__(None, None, None)


@pytest.fixture
def client(make_client: Callable[..., TestClient]) -> TestClient:
    return make_client()


@pytest.fixture
def model(client: TestClient) -> SentimentModel:
    """The model instance loaded by `client`'s app."""
    return client.app.state.model
