from __future__ import annotations

from fastapi import APIRouter

from app.dependencies import DbSession, FiltersDep, SettingsDep
from app.schemas.analytics import AnalyticsSummary
from app.schemas.common import error_responses
from app.services import analytics as analytics_service

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get(
    "/summary",
    response_model=AnalyticsSummary,
    summary="Dashboard aggregates: distribution, trend over time, cache and model usage",
    responses=error_responses(422),
)
def summary(filters: FiltersDep, session: DbSession, settings: SettingsDep) -> AnalyticsSummary:
    return analytics_service.build_summary(session, filters, settings.low_confidence_threshold)
