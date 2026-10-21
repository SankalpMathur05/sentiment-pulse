"""Model card returned by GET /api/model, read from the artifact's metadata.json."""
from __future__ import annotations

from pydantic import BaseModel

from app.schemas.common import TopWord


class DatasetInfo(BaseModel):
    name: str
    homepage: str
    licence: str
    rows_train: int
    rows_test: int


class ClassMetrics(BaseModel):
    precision: float
    recall: float
    f1: float
    support: int


class ModelMetrics(BaseModel):
    accuracy: float
    macro_precision: float
    macro_recall: float
    macro_f1: float
    weighted_f1: float
    per_class: dict[str, ClassMetrics]
    confusion_matrix: list[list[int]]
    confusion_labels: list[str]
    log_loss: float | None = None
    brier_score: float | None = None


class ModelComparison(BaseModel):
    model: str
    cv_macro_f1: float
    cv_macro_f1_std: float | None = None
    test_macro_f1: float
    test_accuracy: float
    selected: bool


class ModelInfo(BaseModel):
    name: str
    version: str
    semver: str
    trained_at: str
    sklearn_version: str
    preprocessing_version: str
    labels: list[str]
    low_confidence_threshold: float
    dataset: DatasetInfo
    metrics: ModelMetrics
    comparison: list[ModelComparison]
    top_features: dict[str, list[TopWord]]
    limitations: list[str]
