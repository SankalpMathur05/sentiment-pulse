from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class ModelCheck(BaseModel):
    status: Literal["ok", "down"]
    version: str | None


class DependencyCheck(BaseModel):
    status: Literal["ok", "down", "disabled"]
    latency_ms: float | None = None
    error: str | None = None


class HealthChecks(BaseModel):
    model: ModelCheck
    database: DependencyCheck
    redis: DependencyCheck


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded", "down"]
    version: str
    environment: str
    uptime_seconds: float
    checks: HealthChecks


class LivenessResponse(BaseModel):
    status: Literal["alive"]
