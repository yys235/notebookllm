"""Share link business logic service."""
import secrets
import uuid
from datetime import datetime, timezone, timedelta

from sqlalchemy import desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from app.core.config import get_settings
from app.core.security import verify_password, get_password_hash
from app.models.share import ShareLink
from app.schemas.share import ShareLinkCreate, ShareLinkUpdate

settings = get_settings()


class ShareService:
    """Service for share link operations."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize share service.

        Args:
            db: Database session
        """
        self.db = db

    async def get_by_id(self, link_id: str | uuid.UUID, user_id: str | uuid.UUID) -> ShareLink | None:
        """Get share link by ID for a specific user.

        Args:
            link_id: Share link ID
            user_id: User ID

        Returns:
            ShareLink | None: Share link or None
        """
        query = select(ShareLink).where(
            and_(
                ShareLink.id == link_id,
                ShareLink.user_id == user_id,
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_token(self, token: str) -> ShareLink | None:
        """Get share link by token.

        Args:
            token: Share token

        Returns:
            ShareLink | None: Share link or None
        """
        query = select(ShareLink).where(
            ShareLink.token == token
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_links(
        self,
        user_id: str | uuid.UUID,
        page: int = 1,
        page_size: int = 20,
        note_id: str | uuid.UUID | None = None,
        active_only: bool = False,
    ) -> tuple[list[ShareLink], int]:
        """List share links for a user.

        Args:
            user_id: User ID
            page: Page number
            page_size: Items per page
            note_id: Filter by note ID
            active_only: Only show active links

        Returns:
            tuple: (links, total_count)
        """
        conditions = [ShareLink.user_id == user_id]

        if note_id:
            conditions.append(ShareLink.note_id == note_id)

        if active_only:
            conditions.append(ShareLink.is_active == True)

        query = select(ShareLink).where(
            and_(*conditions)
        ).order_by(desc(ShareLink.created_at))

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # Get paginated links
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        result = await self.db.execute(query)
        links = result.scalars().all()

        return list(links), total

    async def create(self, user_id: str | uuid.UUID, data: ShareLinkCreate) -> ShareLink:
        """Create a new share link.

        Args:
            user_id: User ID
            data: Share link creation data

        Returns:
            ShareLink: Created share link
        """
        # Generate unique token
        token = secrets.token_urlsafe(32)

        # Calculate expiration
        expires_at = None
        if data.expires_in_hours:
            expires_at = datetime.now(timezone.utc) + timedelta(hours=data.expires_in_hours)

        # Hash password if provided
        password_hash = None
        if data.password:
            password_hash = get_password_hash(data.password)

        link = ShareLink(
            user_id=user_id,
            note_id=data.note_id,
            token=token,
            password_hash=password_hash,
            max_access_count=data.max_access_count,
            expires_at=expires_at,
        )
        self.db.add(link)
        await self.db.commit()
        await self.db.refresh(link)
        return link

    async def update(
        self,
        link: ShareLink,
        data: ShareLinkUpdate,
    ) -> ShareLink:
        """Update share link settings.

        Args:
            link: Share link to update
            data: Update data

        Returns:
            ShareLink: Updated link
        """
        if data.expires_in_hours is not None:
            link.expires_at = datetime.now(timezone.utc) + timedelta(hours=data.expires_in_hours)

        if data.password is not None:
            if data.password:
                link.password_hash = get_password_hash(data.password)
            else:
                link.password_hash = None

        if data.max_access_count is not None:
            link.max_access_count = data.max_access_count

        await self.db.commit()
        await self.db.refresh(link)
        return link

    async def revoke(self, link: ShareLink) -> ShareLink:
        """Revoke a share link.

        Args:
            link: Share link to revoke

        Returns:
            ShareLink: Revoked link
        """
        link.is_active = False
        await self.db.commit()
        await self.db.refresh(link)
        return link

    async def reactivate(self, link: ShareLink) -> ShareLink:
        """Reactivate a revoked share link.

        Args:
            link: Share link to reactivate

        Returns:
            ShareLink: Reactivated link
        """
        link.is_active = True
        await self.db.commit()
        await self.db.refresh(link)
        return link

    async def delete(self, link: ShareLink) -> None:
        """Permanently delete a share link.

        Args:
            link: Share link to delete
        """
        await self.db.delete(link)
        await self.db.commit()

    async def verify_password(self, link: ShareLink, password: str) -> bool:
        """Verify password for a protected share link.

        Args:
            link: Share link
            password: Password to verify

        Returns:
            bool: True if password matches or no password set
        """
        if not link.password_hash:
            return True
        return verify_password(password, link.password_hash)

    async def record_access(self, link: ShareLink) -> ShareLink:
        """Record access to a share link.

        Args:
            link: Share link being accessed

        Returns:
            ShareLink: Updated link
        """
        link.last_accessed_at = datetime.now(timezone.utc)
        link.access_count += 1

        # Auto-revoke if max access count reached
        if link.max_access_count > 0 and link.access_count >= link.max_access_count:
            link.is_active = False

        await self.db.commit()
        await self.db.refresh(link)
        return link

    async def is_valid(self, link: ShareLink) -> tuple[bool, str | None]:
        """Check if share link is valid.

        Args:
            link: Share link to validate

        Returns:
            tuple: (is_valid, error_message)
        """
        if not link.is_active:
            return False, "Share link has been revoked"

        if link.expires_at and link.expires_at < datetime.now(timezone.utc):
            return False, "Share link has expired"

        if link.max_access_count > 0 and link.access_count >= link.max_access_count:
            return False, "Maximum access count reached"

        return True, None

    def get_share_url(self, token: str) -> str:
        """Generate full share URL for a token.

        Args:
            token: Share token

        Returns:
            str: Full share URL
        """
        # In production, this should use the actual frontend URL
        return f"{settings.CORS_ORIGINS[0]}/shared/{token}" if settings.CORS_ORIGINS else f"/shared/{token}"

    def to_read_model(self, link: ShareLink) -> dict:
        """Convert ShareLink to read model dict with computed fields.

        Args:
            link: ShareLink entity

        Returns:
            dict: Read model data
        """
        remaining = None
        if link.max_access_count > 0:
            remaining = max(0, link.max_access_count - link.access_count)

        is_expired = bool(
            link.expires_at and link.expires_at < datetime.now(timezone.utc)
        )

        return {
            "id": str(link.id),
            "note_id": str(link.note_id),
            "token": link.token,
            "has_password": bool(link.password_hash),
            "max_access_count": link.max_access_count,
            "is_active": link.is_active,
            "expires_at": link.expires_at,
            "created_at": link.created_at,
            "last_accessed_at": link.last_accessed_at,
            "access_count": link.access_count,
            "remaining_accesses": remaining,
            "is_expired": is_expired,
            "share_url": self.get_share_url(link.token),
        }
