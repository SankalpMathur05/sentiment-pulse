from __future__ import annotations

from fastapi import APIRouter

from app.dependencies import ModelDep, SettingsDep
from app.schemas.common import error_responses
from app.schemas.model import ModelInfo

router = APIRouter(prefix="/model", tags=["Model"])


@router.get(
    "",
    response_model=ModelInfo,
    summary="Model card: version, dataset, metrics",
    responses=error_responses(503),
)
def model_info(model: ModelDep, settings: SettingsDep) -> ModelInfo:
    """Everything here is read from the artifact's metadata.json, written at training time."""
    metadata = model.metadata
    return ModelInfo(
        name=metadata["name"],
        version=model.version,
        semver=metadata["semver"],
        trained_at=metadata["trained_at"],
        sklearn_version=metadata["sklearn_version"],
        preprocessing_version=metadata["preprocessing_version"],
        labels=model.labels,
        low_confidence_threshold=settings.low_confidence_threshold,
        dataset=metadata["dataset"],
        metrics=metadata["metrics"],
        comparison=metadata["comparison"],
        top_features=metadata["top_features"],
        limitations=metadata["limitations"],
    )
