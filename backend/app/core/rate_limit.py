"""Rate limiting utilities using slowapi."""
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, HTTPException, status
from typing import Callable

from app.core.config import get_settings
from app.core.redis import get_redis

settings = get_settings()

# Rate limiter using Redis for distributed rate limiting
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.REDIS_URL,
    default_limits=["60/minute"] if settings.RATE_LIMIT_ENABLED else [],
    headers_enabled=True,
)


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Custom handler for rate limit exceeded errors."""
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail={
            "error": "Rate limit exceeded",
            "message": f"Too many requests. Please try again later.",
            "retry_after": getattr(exc, 'retry_after', 60),
        }
    )


def get_user_identifier(request: Request) -> str:
    """
    Get a unique identifier for rate limiting.

    Uses user ID from JWT token if authenticated, otherwise falls back to IP address.
    This prevents attackers from using multiple IPs to bypass rate limits.
    """
    # Try to get user ID from JWT token first
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        try:
            from app.core.security import decode_token
            token = auth_header.split(" ")[1]
            payload = decode_token(token)
            if payload and payload.get("sub"):
                # Use user ID for authenticated requests
                return f"user:{payload.get('sub')}"
        except Exception:
            pass

    # Fall back to IP address for unauthenticated requests
    return f"ip:{get_remote_address(request)}"


# Rate limit decorators for different endpoint types
def login_rate_limit(request: Request) -> str:
    """Stricter rate limit for login endpoints (5 per minute)."""
    return get_user_identifier(request)


def strict_rate_limit(request: Request) -> str:
    """Strict rate limit for sensitive operations (10 per minute)."""
    return get_user_identifier(request)


def upload_rate_limit(request: Request) -> str:
    """Rate limit for file uploads (5 per minute)."""
    return get_user_identifier(request)


# Export the limiter for use in routes
__all__ = [
    "limiter",
    "rate_limit_exceeded_handler",
    "get_user_identifier",
    "login_rate_limit",
    "strict_rate_limit",
    "upload_rate_limit",
]
