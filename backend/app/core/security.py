"""Security utilities for authentication and authorization."""
from datetime import datetime, timedelta, timezone
from functools import lru_cache

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@lru_cache
def get_secret_key() -> str:
    """Get JWT secret key."""
    return settings.SECRET_KEY


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash.

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password

    Returns:
        bool: True if password matches
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password.

    Args:
        password: Plain text password

    Returns:
        str: Hashed password
    """
    return pwd_context.hash(password)


def create_access_token(
    data: dict,
    expires_delta: timedelta | None = None,
) -> str:
    """Create JWT access token.

    Args:
        data: Payload data to encode
        expires_delta: Token expiration time delta

    Returns:
        str: Encoded JWT token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, get_secret_key(), algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """Create JWT refresh token.

    Args:
        data: Payload data to encode

    Returns:
        str: Encoded JWT token
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, get_secret_key(), algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict | None:
    """Decode and validate JWT token.

    Args:
        token: JWT token to decode

    Returns:
        dict | None: Decoded payload or None if invalid
    """
    try:
        return jwt.decode(token, get_secret_key(), algorithms=[settings.ALGORITHM])
    except JWTError:
        return None
