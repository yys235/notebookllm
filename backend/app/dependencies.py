"""Common dependencies for route handlers."""
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logger import get_logger
from app.core.redis import get_redis
from redis.asyncio.client import Redis
from app.core.security import decode_token
from app.models.user import User
# TokenPayload not needed - decode_token returns dict
from app.services.user import UserService

logger = get_logger(__name__)

# Type aliases for dependency injection
DBSession = Annotated[AsyncSession, Depends(get_db)]
RedisClient = Annotated[Redis, Depends(get_redis)]


async def get_current_user(
    authorization: Annotated[str, Header()],
    db: DBSession,
) -> User:
    """Get current authenticated user from JWT token.

    Args:
        authorization: Authorization header with Bearer token
        db: Database session

    Returns:
        User: Current user

    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Extract token
    if not authorization.startswith("Bearer "):
        raise credentials_exception
    token = authorization.split(" ")[1]

    # Decode token
    payload = decode_token(token)
    if payload is None:
        raise credentials_exception

    # Validate token type
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    # Get user ID
    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    # Load user from database
    user_service = UserService(db)
    user = await user_service.get_by_id(user_id)
    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Get current active user.

    Args:
        current_user: Current user from token

    Returns:
        User: Current active user

    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )
    return current_user


CurrentUser = Annotated[User, Depends(get_current_active_user)]
