"""Redis connection and client management."""
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from redis.asyncio import ConnectionPool, Redis

from app.core.config import get_settings

settings = get_settings()

# Create connection pool
redis_pool: ConnectionPool = aioredis.ConnectionPool.from_url(
    settings.REDIS_URL,
    max_connections=settings.REDIS_POOL_SIZE,
    decode_responses=True,
)


async def get_redis() -> Redis:
    """Get Redis client.

    Returns:
        Redis: Redis client instance
    """
    return Redis(connection_pool=redis_pool)


@asynccontextmanager
async def get_redis_context() -> Redis:
    """Get Redis client as context manager.

    Yields:
        Redis: Redis client instance

    Example:
        async with get_redis_context() as redis:
            await redis.set("key", "value")
    """
    redis = Redis(connection_pool=redis_pool)
    try:
        yield redis
    finally:
        await redis.close()


async def close_redis() -> None:
    """Close Redis connection pool."""
    await redis_pool.disconnect()
