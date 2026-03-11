"""Rate limiting utilities using Redis."""
from functools import lru_cache

from redis.asyncio import Redis
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import get_settings

settings = get_settings()


class RateLimiter:
    """Token bucket rate limiter using Redis."""

    def __init__(self, redis: Redis) -> None:
        """Initialize rate limiter.

        Args:
            redis: Redis client instance
        """
        self.redis = redis

    async def is_allowed(
        self,
        key: str,
        limit: int | None = None,
        window: int = 60,
    ) -> bool:
        """Check if request is allowed under rate limit.

        Args:
            key: Unique identifier for rate limit bucket (e.g., user_id, IP)
            limit: Maximum requests allowed (default from settings)
            window: Time window in seconds

        Returns:
            bool: True if request is allowed
        """
        if not settings.RATE_LIMIT_ENABLED:
            return True

        limit = limit or settings.RATE_LIMIT_PER_MINUTE

        try:
            pipe = self.redis.pipeline(transaction=True)
            current = await self.redis.incr(f"rate_limit:{key}")
            if current == 1:
                await self.redis.expire(f"rate_limit:{key}", window)
            return current <= limit
        except Exception:
            # Fail open on Redis errors
            return True

    async def get_remaining(self, key: str, limit: int | None = None) -> int:
        """Get remaining requests for a key.

        Args:
            key: Rate limit key
            limit: Maximum requests allowed

        Returns:
            int: Remaining requests
        """
        limit = limit or settings.RATE_LIMIT_PER_MINUTE
        try:
            current = int(await self.redis.get(f"rate_limit:{key}") or 0)
            return max(0, limit - current)
        except Exception:
            return limit


async def check_rate_limit(
    redis: Redis,
    key: str,
    limit: int | None = None,
) -> bool:
    """Check rate limit and raise exception if exceeded.

    Args:
        redis: Redis client
        key: Rate limit key
        limit: Request limit

    Returns:
        bool: True if allowed

    Raises:
        HTTPException: If rate limit exceeded
    """
    limiter = RateLimiter(redis)
    if not await limiter.is_allowed(key, limit):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": "60"},
        )
    return True
