"""HTTP routes. Business endpoints live under /api; health checks stay at the root (/health)
where hosting platforms and load balancers expect them."""
from fastapi import APIRouter

from app.api.routes import analytics, cache, health, model, predict, predictions

api_router = APIRouter(prefix="/api")
api_router.include_router(predict.router)
api_router.include_router(predictions.router)
api_router.include_router(analytics.router)
api_router.include_router(cache.router)
api_router.include_router(model.router)

health_router = health.router
