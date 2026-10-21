from __future__ import annotations

from fastapi import APIRouter

from app.dependencies import CacheDep
from app.schemas.cache import CacheStatsResponse

router = APIRouter(prefix="/cache", tags=["Cache"])


@router.get("/stats", response_model=CacheStatsResponse, summary="Redis cache statistics")
def cache_stats(cache: CacheDep) -> CacheStatsResponse:
    """Never fails because of Redis: if it is unreachable, `available` is false."""
    return cache.stats()
