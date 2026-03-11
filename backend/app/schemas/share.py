"""Share link related schemas."""
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ShareLinkCreate(BaseModel):
    """Schema for creating a share link."""

    note_id: str = Field(..., description="Note ID to share")
    expires_in_hours: int | None = Field(
        None,
        ge=1,
        le=8760,
        description="Expiration in hours (max 1 year), None for never expire",
    )
    password: str | None = Field(
        None,
        min_length=4,
        max_length=128,  # Allow SHA-256 hash (64 chars) or plain password
        description="Optional password protection (plain text or SHA-256 hash)",
    )
    max_access_count: int = Field(
        default=0,
        ge=0,
        le=10000,
        description="Maximum number of accesses (0 = unlimited)",
    )


class ShareLinkRead(BaseModel):
    """Schema for share link response."""

    id: str = Field(..., description="Share link ID")
    note_id: str = Field(..., description="Shared note ID")
    token: str = Field(..., description="Share token")
    has_password: bool = Field(..., description="Whether link has password protection")
    max_access_count: int = Field(..., description="Maximum access count (0 = unlimited)")
    is_active: bool = Field(..., description="Link active status")
    expires_at: datetime | None = Field(None, description="Expiration timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")
    last_accessed_at: datetime | None = Field(None, description="Last access timestamp")
    access_count: int = Field(..., description="Number of accesses")
    remaining_accesses: int | None = Field(
        None,
        description="Remaining accesses (None if unlimited)",
    )
    is_expired: bool = Field(..., description="Whether link is expired")
    share_url: str = Field(..., description="Full share URL")

    model_config = {"from_attributes": True}


class SharedNoteRead(BaseModel):
    """Schema for shared note content (public access)."""

    id: uuid.UUID = Field(..., description="Note ID")
    title: str = Field(..., description="Note title")
    content: str = Field(..., description="Note content")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = {"from_attributes": True}


class ShareLinkPasswordCheck(BaseModel):
    """Schema for password-protected share access."""

    password: str | None = Field(None, min_length=4, max_length=128, description="Share link password (optional)")


class ShareLinkUpdate(BaseModel):
    """Schema for updating share link settings."""

    expires_in_hours: int | None = Field(
        None,
        ge=1,
        le=8760,
        description="Update expiration time in hours",
    )
    password: str | None = Field(
        None,
        min_length=4,
        max_length=128,  # Allow SHA-256 hash (64 chars) or plain password
        description="Update password (null to remove)",
    )
    max_access_count: int | None = Field(
        None,
        ge=0,
        le=10000,
        description="Update max access count (0 = unlimited)",
    )
