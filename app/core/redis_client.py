"""Redis async connection pool for caching and Celery broker."""
from __future__ import annotations

import redis.asyncio as aioredis
from app.config import settings

_pool: aioredis.Redis | None = None


def get_redis_pool() -> aioredis.Redis:
    """Return the shared async Redis connection, creating it lazily on first call."""
    global _pool
    if _pool is None:
        _pool = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            max_connections=10,
        )
    return _pool


async def get_redis() -> aioredis.Redis:
    """FastAPI dependency — returns the shared async Redis connection."""
    return get_redis_pool()
