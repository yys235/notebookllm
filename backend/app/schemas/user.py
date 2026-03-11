"""User-related schemas."""
from datetime import datetime
from typing import Literal
from uuid import UUID
from re import Pattern

from pydantic import BaseModel, EmailStr, Field, field_validator, IPvAnyAddress
import re


class UserBase(BaseModel):
    """Base user schema with common fields."""

    email: EmailStr = Field(..., description="User email address")
    username: str = Field(..., min_length=3, max_length=100, description="Username")
    full_name: str | None = Field(None, max_length=255, description="Full name")


class UserCreate(UserBase):
    """Schema for creating a new user."""

    password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="Password (min 8 characters)",
    )

    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password meets security requirements.

        Args:
            v: Password to validate

        Returns:
            str: Validated password

        Raises:
            ValueError: If password doesn't meet requirements
        """
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")

        # Check for at least one lowercase letter
        if not re.search(r'[a-z]', v):
            raise ValueError("Password must contain at least one lowercase letter")

        # Check for at least one uppercase letter
        if not re.search(r'[A-Z]', v):
            raise ValueError("Password must contain at least one uppercase letter")

        # Check for at least one digit
        if not re.search(r'\d', v):
            raise ValueError("Password must contain at least one digit")

        # Check for at least one special character
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]', v):
            raise ValueError("Password must contain at least one special character")

        # Check for common weak passwords
        weak_passwords = {
            "password", "12345678", "abcdefgh", "qwerty123",
            "password123", "admin123", "letmein", "welcome"
        }
        if v.lower() in weak_passwords:
            raise ValueError("Password is too common and weak")

        return v


class UserUpdate(BaseModel):
    """Schema for updating user information."""

    email: EmailStr | None = None
    username: str | None = Field(None, min_length=3, max_length=100)
    full_name: str | None = Field(None, max_length=255)
    password: str | None = Field(None, min_length=8, max_length=100)

    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v: str | None) -> str | None:
        """Validate password meets security requirements."""
        if v is None:
            return v
        # Use same validation as UserCreate
        return UserCreate.validate_password_strength(v)


class UserRead(UserBase):
    """Schema for user response."""

    id: str = Field(..., description="User ID")
    is_active: bool = Field(..., description="Account active status")
    is_verified: bool = Field(..., description="Email verification status")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    last_login_at: datetime | None = Field(None, description="Last login timestamp")

    @field_validator('id', mode='before')
    @classmethod
    def convert_uuid(cls, v):
        """Convert UUID to string."""
        if isinstance(v, UUID):
            return str(v)
        return v

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """Schema for token response."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: Literal["bearer"] = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiration in seconds")


class LoginRequest(BaseModel):
    """Schema for login request."""

    username: str = Field(..., description="Username or email")
    password: str = Field(..., description="Password")


class RegisterRequest(UserCreate):
    """Schema for registration request."""

    confirm_password: str = Field(..., description="Confirm password")

    @field_validator('confirm_password')
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        """Validate that passwords match."""
        if 'password' in info.data and v != info.data['password']:
            raise ValueError("Passwords do not match")
        return v


class RefreshTokenRequest(BaseModel):
    """Schema for refresh token request."""

    refresh_token: str = Field(..., description="Refresh token")


class ChangePasswordRequest(BaseModel):
    """Schema for password change request."""

    old_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, max_length=100, description="New password")

    @field_validator('new_password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password meets security requirements."""
        return UserCreate.validate_password_strength(v)


class PasswordResetRequest(BaseModel):
    """Schema for password reset request."""

    email: EmailStr = Field(..., description="User email")


class PasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation."""

    token: str = Field(..., description="Reset token")
    new_password: str = Field(..., min_length=8, max_length=100, description="New password")

    @field_validator('new_password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password meets security requirements."""
        return UserCreate.validate_password_strength(v)


class SessionInfo(BaseModel):
    """Schema for active session information."""

    id: str = Field(..., description="Session ID")
    created_at: datetime = Field(..., description="Session creation time")
    expires_at: datetime = Field(..., description="Session expiration time")
    user_agent: str | None = Field(None, description="Browser/user agent")
    ip_address: str | None = Field(None, description="IP address")
    is_current: bool = Field(..., description="Is this the current session")

    model_config = {"from_attributes": True}
