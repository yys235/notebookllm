"""Share link routes."""
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logger import get_logger
from app.core.security import verify_password
from app.dependencies import CurrentUser
from app.models.note import Note
from app.models.share import ShareLink
from app.schemas.common import ErrorResponse, PaginatedResponse
from app.schemas.note import NoteRead
from app.schemas.share import (
    ShareLinkCreate,
    ShareLinkPasswordCheck,
    ShareLinkRead,
    ShareLinkUpdate,
    SharedNoteRead,
)
from app.services.note import NoteService
from app.services.share import ShareService
from app.utils.pagination import create_pagination_response

router = APIRouter()
logger = get_logger(__name__)

# Type aliases
DBSession = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=PaginatedResponse[ShareLinkRead])
async def list_share_links(
    current_user: CurrentUser,
    db: DBSession,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    note_id: str | None = Query(None, description="Filter by note ID"),
    active_only: bool = Query(False, description="Only show active links"),
):
    """List share links for current user.

    Supports filtering by note and active status.
    """
    service = ShareService(db)
    links, total = await service.list_links(
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        note_id=note_id,
        active_only=active_only,
    )

    # Convert to read models with computed fields
    items = [ShareLinkRead(**service.to_read_model(link)) for link in links]
    return PaginatedResponse.create(items, total, page, page_size)


@router.post("", response_model=ShareLinkRead, status_code=status.HTTP_201_CREATED)
async def create_share_link(
    data: ShareLinkCreate,
    current_user: CurrentUser,
    db: DBSession,
):
    """Create a new share link for a note.

    Sharing rules:
    - Public notes: can only be shared without password
    - Private notes: must have password if no expiration is set

    Features:
    - Optional password protection (required for private notes without expiration)
    - Optional expiration time
    - Optional max access count limit
    """
    # Verify note ownership and get note
    note_service = NoteService(db)
    note = await note_service.get_by_id(data.note_id, user_id=current_user.id)
    if note is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found",
        )

    note_visibility = getattr(note, 'visibility', 'private')

    # Validate sharing rules based on note visibility
    if note_visibility == 'public':
        # Public notes: cannot have password
        if data.password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Public notes can only be shared without password",
            )
    else:
        # Private notes: must have password if no expiration
        if not data.expires_in_hours and not data.password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Private notes must have a password if no expiration time is set",
            )

    service = ShareService(db)
    link = await service.create(user_id=current_user.id, data=data)

    logger.info(
        "Share link created",
        user_id=str(current_user.id),
        note_id=str(data.note_id),
        link_id=str(link.id),
        note_visibility=note_visibility,
    )

    return ShareLinkRead(**service.to_read_model(link))


@router.get("/{link_id}", response_model=ShareLinkRead)
async def get_share_link(
    link_id: str,
    current_user: CurrentUser,
    db: DBSession,
):
    """Get details of a specific share link."""
    service = ShareService(db)
    link = await service.get_by_id(link_id, user_id=current_user.id)

    if link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share link not found",
        )

    return ShareLinkRead(**service.to_read_model(link))


@router.patch("/{link_id}", response_model=ShareLinkRead)
async def update_share_link(
    link_id: str,
    data: ShareLinkUpdate,
    current_user: CurrentUser,
    db: DBSession,
):
    """Update share link settings.

    Can update:
    - Expiration time
    - Password (set, change, or remove)
    - Max access count
    """
    service = ShareService(db)
    link = await service.get_by_id(link_id, user_id=current_user.id)

    if link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share link not found",
        )

    updated = await service.update(link, data)

    logger.info(
        "Share link updated",
        user_id=str(current_user.id),
        link_id=str(link_id),
    )

    return ShareLinkRead(**service.to_read_model(updated))


@router.post("/{link_id}/revoke", response_model=ShareLinkRead)
async def revoke_share_link(
    link_id: str,
    current_user: CurrentUser,
    db: DBSession,
):
    """Revoke a share link (can be reactivated later)."""
    service = ShareService(db)
    link = await service.get_by_id(link_id, user_id=current_user.id)

    if link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share link not found",
        )

    revoked = await service.revoke(link)

    logger.info(
        "Share link revoked",
        user_id=str(current_user.id),
        link_id=str(link_id),
    )

    return ShareLinkRead(**service.to_read_model(revoked))


@router.post("/{link_id}/reactivate", response_model=ShareLinkRead)
async def reactivate_share_link(
    link_id: str,
    current_user: CurrentUser,
    db: DBSession,
):
    """Reactivate a previously revoked share link."""
    service = ShareService(db)
    link = await service.get_by_id(link_id, user_id=current_user.id)

    if link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share link not found",
        )

    reactivated = await service.reactivate(link)

    logger.info(
        "Share link reactivated",
        user_id=str(current_user.id),
        link_id=str(link_id),
    )

    return ShareLinkRead(**service.to_read_model(reactivated))


@router.delete("/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_share_link(
    link_id: str,
    current_user: CurrentUser,
    db: DBSession,
):
    """Permanently delete a share link."""
    service = ShareService(db)
    link = await service.get_by_id(link_id, user_id=current_user.id)

    if link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share link not found",
        )

    await service.delete(link)

    logger.info(
        "Share link deleted",
        user_id=str(current_user.id),
        link_id=str(link_id),
    )


@router.get("/public/{token}/info")
async def get_share_link_info(
    token: str,
    db: DBSession,
):
    """Get share link info without accessing the note.

    Returns whether the link is protected, active, expired, and note visibility.
    Does not increment access count.
    """
    service = ShareService(db)
    link = await service.get_by_token(token)

    if link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share link not found",
        )

    # Get note to check visibility
    note_service = NoteService(db)
    note = await note_service.get_by_id(link.note_id, user_id=link.user_id)
    note_visibility = getattr(note, 'visibility', 'private') if note else 'private'

    is_valid, error_msg = await service.is_valid(link)

    return {
        "token": token,
        "has_password": bool(link.password_hash),
        "is_valid": is_valid,
        "error": error_msg,
        "expires_at": link.expires_at,
        "note_visibility": note_visibility,
        "requires_password": note_visibility == 'private' and bool(link.password_hash),
    }


@router.post("/public/{token}/access", response_model=SharedNoteRead)
async def access_shared_note(
    token: str,
    request: Request,
    db: DBSession,
    password_check: ShareLinkPasswordCheck | None = None,
):
    """Access a shared note via token.

    Access logic (note visibility takes highest priority):
    - If note is public: allow access without password (public notes can only have passwordless shares)
    - If note is private: require password verification

    Implements IP-based rate limiting for password attempts.
    Increments access count on successful access.
    """
    service = ShareService(db)
    link = await service.get_by_token(token)

    if link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share link not found",
        )

    # Validate link (check expiration, active status, access count)
    is_valid, error_msg = await service.is_valid(link)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=error_msg or "Share link is invalid",
        )

    # Get note to check visibility
    note_service = NoteService(db)
    note = await note_service.get_by_id(link.note_id, user_id=link.user_id)

    if note is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found",
        )

    # Check note visibility - this takes highest priority
    note_visibility = getattr(note, 'visibility', 'private')

    if note_visibility == 'public':
        # Public notes: no password needed (and share links shouldn't have passwords)
        pass
    else:
        # Private notes: only require password if share link has password protection
        if link.password_hash:
            # Verify password
            if not password_check or not await service.verify_password(link, password_check.password):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid password",
                )
        # If no password_hash, the share was created with expiration, allow access

    # Record access
    await service.record_access(link)

    logger.info(
        "Share link accessed",
        link_id=str(link.id),
        note_visibility=note_visibility,
        access_count=link.access_count,
    )

    return SharedNoteRead.model_validate(note)


@router.get("/public/{token}", response_model=SharedNoteRead, deprecated=True)
async def get_shared_note_legacy(
    token: str,
    db: DBSession,
):
    """Legacy endpoint: Get shared note via token (no password support).

    Deprecated: Use /public/{token}/access instead.
    """
    service = ShareService(db)
    link = await service.get_by_token(token)

    if link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share link not found",
        )

    # Reject password-protected links
    if link.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This link requires a password. Use the /access endpoint.",
        )

    is_valid, error_msg = await service.is_valid(link)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=error_msg or "Share link is invalid",
        )

    await service.record_access(link)

    note_service = NoteService(db)
    note = await note_service.get_by_id(link.note_id, user_id=link.user_id)

    if note is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found",
        )

    return SharedNoteRead.model_validate(note)
