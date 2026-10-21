from __future__ import annotations

from pydantic import BaseModel, Field


class CacheStatsResponse(BaseModel):
    enabled: bool = Field(description="CACHE_ENABLED setting.")
    available: bool = Field(description="Whether Redis answered just now.")
    ttl_seconds: int
    keys: int | None = Field(description="Cached predictions (sentiment:v1:* keys), counted up to a cap.")
    hits: int | None = Field(description="Redis keyspace_hits. Server-wide, so it includes other key types.")
    misses: int | None = Field(description="Redis keyspace_misses. Server-wide.")
    hit_rate: float | None = Field(description="hits / (hits + misses), server-wide.")
    used_memory_human: str | None
