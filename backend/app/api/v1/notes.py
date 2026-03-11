"""Note management routes."""
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logger import get_logger
from app.dependencies import CurrentUser
from app.schemas.common import PaginatedResponse
from app.schemas.note import (
    BatchDeleteRequest,
    BatchUpdateRequest,
    NoteCreate,
    NoteRead,
    NoteRestoreRequest,
    NoteSummary,
    NoteUpdate,
    NoteVersionRead,
)
from app.services.note import NoteService
from app.utils.pagination import create_pagination_response

router = APIRouter()
logger = get_logger(__name__)


def validate_uuid(uuid_str: str, field_name: str = "ID") -> UUID:
    """Validate and convert string to UUID."""
    try:
        return UUID(uuid_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {field_name} format",
        )

# Type aliases
DBSession = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=PaginatedResponse[NoteSummary])
async def list_notes(
    current_user: CurrentUser,
    db: DBSession,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    pinned_only: bool = Query(False, description="Only show pinned notes"),
    category_id: str | None = Query(None, description="Filter by category ID"),
    search: str | None = Query(None, description="Search in title and content"),
    sort_by: Literal["updated_at", "created_at", "title"] = Query(
        "updated_at", description="Field to sort by"
    ),
    sort_order: Literal["asc", "desc"] = Query("desc", description="Sort direction"),
):
    """List notes for current user with filtering and sorting.

    Supports:
    - Pagination
    - Search (title + content)
    - Filter by category and pinned status
    - Sort by various fields
    """
    service = NoteService(db)
    notes, total = await service.list_notes(
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        pinned_only=pinned_only,
        category_id=category_id,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    # Convert to summary with preview
    items = [
        NoteSummary(
            **note.__dict__,
            preview=NoteService.get_preview(note.content),
        )
        for note in notes
    ]

    return PaginatedResponse.create(items, total, page, page_size)


@router.post("", response_model=NoteRead, status_code=status.HTTP_201_CREATED)
async def create_note(
    data: NoteCreate,
    current_user: CurrentUser,
    db: DBSession,
):
    """Create a new note.

    Automatically creates an initial version for change tracking.
    """
    service = NoteService(db)
    note = await service.create(user_id=current_user.id, data=data)

    logger.info(
        "Note created",
        user_id=str(current_user.id),
        note_id=str(note.id),
    )

    return NoteRead.model_validate(note)


@router.get("/{note_id}", response_model=NoteRead)
async def get_note(
    note_id: str,
    current_user: CurrentUser,
    db: DBSession,
):
    """Get a specific note by ID."""
    # Validate UUID format
    validate_uuid(note_id, "note_id")

    service = NoteService(db)
    note = await service.get_by_id(note_id, user_id=current_user.id)

    if note is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found",
        )

    return NoteRead.model_validate(note)


@router.patch("/{note_id}", response_model=NoteRead)
async def update_note(
    note_id: str,
    data: NoteUpdate,
    current_user: CurrentUser,
    db: DBSession,
    change_summary: str | None = Query(None, description="Description of changes"),
):
    """Update a note.

    Automatically creates a version snapshot before updating content.
    """
    service = NoteService(db)
    note = await service.get_by_id(note_id, user_id=current_user.id)

    if note is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found",
        )

    updated = await service.update(note, data, change_summary)

    logger.info(
        "Note updated",
        user_id=str(current_user.id),
        note_id=str(note_id),
    )

    return NoteRead.model_validate(updated)


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: str,
    current_user: CurrentUser,
    db: DBSession,
):
    """Soft delete a note.

    The note is marked as deleted but can be restored.
    Use DELETE /notes/trash to permanently delete.
    """
    service = NoteService(db)
    note = await service.get_by_id(note_id, user_id=current_user.id)

    if note is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found",
        )

    await service.soft_delete(note)

    logger.info(
        "Note deleted (soft)",
        user_id=str(current_user.id),
        note_id=str(note_id),
    )


@router.post("/{note_id}/restore", response_model=NoteRead)
async def restore_note(
    note_id: str,
    current_user: CurrentUser,
    db: DBSession,
):
    """Restore a soft-deleted note."""
    service = NoteService(db)
    note = await service.get_by_id(note_id, user_id=current_user.id, include_deleted=True)

    if note is None or not note.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deleted note not found",
        )

    restored = await service.restore(note)

    logger.info(
        "Note restored",
        user_id=str(current_user.id),
        note_id=str(note_id),
    )

    return NoteRead.model_validate(restored)


# ========================================
# Version History
# ========================================


@router.get("/{note_id}/versions", response_model=list[NoteVersionRead])
async def get_note_versions(
    note_id: str,
    current_user: CurrentUser,
    db: DBSession,
):
    """Get version history for a note.

    Returns all versions in reverse chronological order.
    """
    service = NoteService(db)
    versions = await service.get_versions(note_id, user_id=current_user.id)

    return [NoteVersionRead.model_validate(v) for v in versions]


@router.get("/{note_id}/versions/{version_id}", response_model=NoteVersionRead)
async def get_note_version(
    note_id: str,
    version_id: str,
    current_user: CurrentUser,
    db: DBSession,
):
    """Get a specific version of a note."""
    service = NoteService(db)
    version = await service.get_version_by_id(version_id, user_id=current_user.id)

    if version is None or str(version.note_id) != note_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Version not found",
        )

    return NoteVersionRead.model_validate(version)


@router.post("/{note_id}/versions/restore", response_model=NoteRead)
async def restore_note_from_version(
    note_id: str,
    data: NoteRestoreRequest,
    current_user: CurrentUser,
    db: DBSession,
):
    """Restore a note to a specific version.

    Creates a version of the current state before restoring.
    """
    service = NoteService(db)
    note = await service.get_by_id(note_id, user_id=current_user.id)

    if note is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found",
        )

    version = await service.get_version_by_id(data.version_id, user_id=current_user.id)

    if version is None or str(version.note_id) != note_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Version not found",
        )

    restored = await service.restore_from_version(note, version)

    logger.info(
        "Note restored from version",
        user_id=str(current_user.id),
        note_id=str(note_id),
        version_number=version.version_number,
    )

    return NoteRead.model_validate(restored)


# ========================================
# Batch Operations
# ========================================


@router.post("/batch/update", response_model=dict[str, int])
async def batch_update_notes(
    data: BatchUpdateRequest,
    current_user: CurrentUser,
    db: DBSession,
):
    """Batch update multiple notes.

    Can update pin status and category for up to 50 notes at once.
    Returns the number of notes updated.
    """
    service = NoteService(db)
    count = await service.batch_update(
        note_ids=data.note_ids,
        user_id=current_user.id,
        is_pinned=data.is_pinned,
        category_id=data.category_id,
    )

    logger.info(
        "Batch update notes",
        user_id=str(current_user.id),
        count=count,
    )

    return {"updated": count}


@router.post("/batch/delete", response_model=dict[str, int])
async def batch_delete_notes(
    data: BatchDeleteRequest,
    current_user: CurrentUser,
    db: DBSession,
):
    """Batch soft delete multiple notes.

    Deletes up to 50 notes at once.
    Returns the number of notes deleted.
    """
    service = NoteService(db)
    count = await service.batch_delete(
        note_ids=data.note_ids,
        user_id=current_user.id,
    )

    logger.info(
        "Batch delete notes",
        user_id=str(current_user.id),
        count=count,
    )

    return {"deleted": count}


# ========================================
# Trash / Deleted Notes
# ========================================


@router.get("/trash/list", response_model=PaginatedResponse[NoteSummary])
async def list_trash(
    current_user: CurrentUser,
    db: DBSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List soft-deleted notes.

    These notes can be restored or permanently deleted.
    """
    service = NoteService(db)
    notes, total = await service.get_deleted_notes(
        user_id=current_user.id,
        page=page,
        page_size=page_size,
    )

    items = [
        NoteSummary(
            **note.__dict__,
            preview=NoteService.get_preview(note.content),
        )
        for note in notes
    ]

    return PaginatedResponse.create(items, total, page, page_size)


@router.delete("/trash/empty", status_code=status.HTTP_204_NO_CONTENT)
async def empty_trash(
    current_user: CurrentUser,
    db: DBSession,
):
    """Permanently delete all soft-deleted notes.

    This action cannot be undone.
    """
    service = NoteService(db)
    count = await service.empty_trash(user_id=current_user.id)

    logger.info(
        "Trash emptied",
        user_id=str(current_user.id),
        count=count,
    )
