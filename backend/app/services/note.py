"""Note business logic service."""
import uuid
from datetime import datetime, timezone
from typing import Literal

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.note import Note, NoteAttachment, NoteVersion
from app.schemas.note import NoteCreate, NoteUpdate


class NoteService:
    """Service for note-related operations."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize note service.

        Args:
            db: Database session
        """
        self.db = db

    async def get_by_id(
        self,
        note_id: str | uuid.UUID,
        user_id: str | uuid.UUID,
        include_deleted: bool = False,
    ) -> Note | None:
        """Get note by ID for a specific user.

        Args:
            note_id: Note ID
            user_id: User ID
            include_deleted: Include soft-deleted notes

        Returns:
            Note | None: Note instance or None
        """
        query = select(Note).where(
            and_(
                Note.id == note_id,
                Note.user_id == user_id,
            )
        )

        if not include_deleted:
            query = query.where(Note.is_deleted == False)

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_notes(
        self,
        user_id: str | uuid.UUID,
        page: int = 1,
        page_size: int = 20,
        pinned_only: bool = False,
        category_id: str | uuid.UUID | None = None,
        search: str | None = None,
        sort_by: Literal["updated_at", "created_at", "title"] = "updated_at",
        sort_order: Literal["asc", "desc"] = "desc",
        include_deleted: bool = False,
    ) -> tuple[list[Note], int]:
        """List notes for a user with filtering and sorting.

        Args:
            user_id: User ID
            page: Page number
            page_size: Items per page
            pinned_only: Only show pinned notes
            category_id: Filter by category
            search: Search in title and content
            sort_by: Field to sort by
            sort_order: Sort direction
            include_deleted: Include soft-deleted notes

        Returns:
            tuple: (notes, total_count)
        """
        # Build base query
        conditions = [Note.user_id == user_id]

        if not include_deleted:
            conditions.append(Note.is_deleted == False)

        if pinned_only:
            conditions.append(Note.is_pinned == True)

        if category_id:
            conditions.append(Note.category_id == category_id)

        if search:
            search_term = f"%{search}%"
            conditions.append(
                or_(
                    Note.title.ilike(search_term),
                    Note.content.ilike(search_term),
                )
            )

        query = select(Note).where(and_(*conditions))

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # Apply sorting
        sort_column = getattr(Note, sort_by, Note.updated_at)
        if sort_order == "desc":
            query = query.order_by(desc(Note.is_pinned), desc(sort_column))
        else:
            query = query.order_by(desc(Note.is_pinned), sort_column)

        # Get paginated notes
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        result = await self.db.execute(query)
        notes = result.scalars().all()

        return list(notes), total

    async def create(
        self,
        user_id: str | uuid.UUID,
        data: NoteCreate,
        change_summary: str | None = None,
    ) -> Note:
        """Create a new note.

        Args:
            user_id: User ID
            data: Note creation data
            change_summary: Optional change summary for initial version

        Returns:
            Note: Created note
        """
        note = Note(
            user_id=user_id,
            title=data.title,
            content=data.content,
            is_pinned=data.is_pinned,
            visibility=data.visibility,
            category_id=data.category_id,
            editor_type=data.editor_type,
        )
        self.db.add(note)
        await self.db.flush()

        # Create initial version
        await self._create_version(note, change_summary or "Initial version")

        await self.db.commit()
        await self.db.refresh(note)
        return note

    async def update(
        self,
        note: Note,
        data: NoteUpdate,
        change_summary: str | None = None,
    ) -> Note:
        """Update a note.

        Args:
            note: Note instance to update
            data: Update data
            change_summary: Optional description of changes

        Returns:
            Note: Updated note
        """
        update_data = data.model_dump(exclude_unset=True)

        # Check if content/title changed for version tracking
        content_changed = "title" in update_data or "content" in update_data

        if content_changed:
            # Create version before updating
            await self._create_version(note, change_summary)

        # Apply updates
        for field, value in update_data.items():
            setattr(note, field, value)

        note.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(note)
        return note

    async def soft_delete(self, note: Note) -> Note:
        """Soft delete a note (mark as deleted).

        Args:
            note: Note instance to delete

        Returns:
            Note: Deleted note
        """
        note.is_deleted = True
        note.deleted_at = datetime.now(timezone.utc)
        note.is_pinned = False  # Unpin when deleted
        await self.db.commit()
        await self.db.refresh(note)
        return note

    async def permanent_delete(self, note: Note) -> None:
        """Permanently delete a note.

        Args:
            note: Note instance to delete
        """
        await self.db.delete(note)
        await self.db.commit()

    async def restore(self, note: Note) -> Note:
        """Restore a soft-deleted note.

        Args:
            note: Note instance to restore

        Returns:
            Note: Restored note
        """
        note.is_deleted = False
        note.deleted_at = None
        await self.db.commit()
        await self.db.refresh(note)
        return note

    async def restore_from_version(
        self,
        note: Note,
        version: NoteVersion,
    ) -> Note:
        """Restore a note to a specific version.

        Args:
            note: Note to restore
            version: Version to restore from

        Returns:
            Note: Restored note
        """
        # Create version of current state before restoring
        await self._create_version(note, f"Before restoring to version {version.version_number}")

        # Restore content from version
        note.title = version.title
        note.content = version.content
        note.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(note)
        return note

    async def get_versions(
        self,
        note_id: str | uuid.UUID,
        user_id: str | uuid.UUID,
    ) -> list[NoteVersion]:
        """Get version history for a note.

        Args:
            note_id: Note ID
            user_id: User ID (for ownership verification)

        Returns:
            list[NoteVersion]: List of versions
        """
        # Verify ownership
        note = await self.get_by_id(note_id, user_id, include_deleted=True)
        if not note:
            return []

        query = select(NoteVersion).where(
            NoteVersion.note_id == note_id
        ).order_by(desc(NoteVersion.created_at))
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_version_by_id(
        self,
        version_id: str | uuid.UUID,
        user_id: str | uuid.UUID,
    ) -> NoteVersion | None:
        """Get a specific version with ownership verification.

        Args:
            version_id: Version ID
            user_id: User ID

        Returns:
            NoteVersion | None: Version or None
        """
        query = (
            select(NoteVersion)
            .join(Note, Note.id == NoteVersion.note_id)
            .where(
                and_(
                    NoteVersion.id == version_id,
                    Note.user_id == user_id,
                )
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def batch_update(
        self,
        note_ids: list[str | uuid.UUID],
        user_id: str | uuid.UUID,
        is_pinned: bool | None = None,
        category_id: str | uuid.UUID | None = None,
    ) -> int:
        """Batch update multiple notes.

        Args:
            note_ids: List of note IDs
            user_id: User ID
            is_pinned: New pin status
            category_id: New category ID

        Returns:
            int: Number of notes updated
        """
        conditions = [
            Note.id.in_(note_ids),
            Note.user_id == user_id,
            Note.is_deleted == False,
        ]

        update_values = {}
        if is_pinned is not None:
            update_values["is_pinned"] = is_pinned
        if category_id is not None:
            update_values["category_id"] = category_id

        if not update_values:
            return 0

        result = await self.db.execute(
            select(Note).where(and_(*conditions))
        )
        notes = result.scalars().all()

        count = 0
        for note in notes:
            for field, value in update_values.items():
                setattr(note, field, value)
            count += 1

        await self.db.commit()
        return count

    async def batch_delete(
        self,
        note_ids: list[str | uuid.UUID],
        user_id: str | uuid.UUID,
    ) -> int:
        """Batch soft delete multiple notes.

        Args:
            note_ids: List of note IDs
            user_id: User ID

        Returns:
            int: Number of notes deleted
        """
        conditions = [
            Note.id.in_(note_ids),
            Note.user_id == user_id,
            Note.is_deleted == False,
        ]

        result = await self.db.execute(
            select(Note).where(and_(*conditions))
        )
        notes = result.scalars().all()

        count = 0
        now = datetime.now(timezone.utc)
        for note in notes:
            note.is_deleted = True
            note.deleted_at = now
            note.is_pinned = False
            count += 1

        await self.db.commit()
        return count

    async def get_deleted_notes(
        self,
        user_id: str | uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Note], int]:
        """Get soft-deleted notes for potential restore.

        Args:
            user_id: User ID
            page: Page number
            page_size: Items per page

        Returns:
            tuple: (notes, total_count)
        """
        query = select(Note).where(
            and_(
                Note.user_id == user_id,
                Note.is_deleted == True,
            )
        ).order_by(desc(Note.deleted_at))

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # Get paginated notes
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        result = await self.db.execute(query)
        notes = result.scalars().all()

        return list(notes), total

    async def empty_trash(self, user_id: str | uuid.UUID) -> int:
        """Permanently delete all soft-deleted notes for a user.

        Args:
            user_id: User ID

        Returns:
            int: Number of notes permanently deleted
        """
        result = await self.db.execute(
            select(Note).where(
                and_(
                    Note.user_id == user_id,
                    Note.is_deleted == True,
                )
            )
        )
        notes = result.scalars().all()

        count = len(notes)
        for note in notes:
            await self.db.delete(note)

        await self.db.commit()
        return count

    async def _create_version(
        self,
        note: Note,
        change_summary: str | None = None,
    ) -> NoteVersion:
        """Create a version snapshot of the note.

        Args:
            note: Note to snapshot
            change_summary: Optional description of changes

        Returns:
            NoteVersion: Created version
        """
        # Get current version number
        query = select(func.count(NoteVersion.id)).where(
            NoteVersion.note_id == note.id
        )
        count = (await self.db.execute(query)).scalar() or 0

        version = NoteVersion(
            note_id=note.id,
            title=note.title,
            content=note.content,
            version_number=count + 1,
            change_summary=change_summary,
        )
        self.db.add(version)
        await self.db.flush()
        return version

    @staticmethod
    def get_preview(content: str, max_length: int = 200) -> str:
        """Get content preview for list views.

        Args:
            content: Note content
            max_length: Maximum preview length

        Returns:
            str: Content preview
        """
        # Strip markdown formatting for preview
        import re

        # Remove markdown headers, links, bold, etc.
        preview = re.sub(r'[#*`\[\]]', '', content)
        preview = re.sub(r'\n+', ' ', preview)
        preview = preview.strip()

        if len(preview) > max_length:
            preview = preview[:max_length].rsplit(' ', 1)[0] + "..."

        return preview
