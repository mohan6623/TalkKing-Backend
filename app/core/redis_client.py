"""Redis async connection pool for caching and Celery broker."""
from __future__ import annotations

import redis.asyncio as aioredis
from app.config import settings

redis_pool = aioredis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    max_connections=10,
)


async def get_redis() -> aioredis.Redis:
    """FastAPI dependency — returns the shared async Redis connection."""
    return redis_pool
