"""Authentication service for token and session management."""
import uuid
from datetime import datetime, timezone, timedelta

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.models.user import RefreshToken
from app.schemas.user import ChangePasswordRequest

settings = get_settings()


class AuthService:
    """Service for authentication operations."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize auth service.

        Args:
            db: Database session
        """
        self.db = db

    async def create_refresh_token(
        self,
        user_id: str | uuid.UUID,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> RefreshToken:
        """Create and store a refresh token.

        Args:
            user_id: User ID
            user_agent: Browser/user agent string
            ip_address: Client IP address

        Returns:
            RefreshToken: Created refresh token
        """
        # Create JWT token
        token_string = create_refresh_token(data={"sub": str(user_id)})

        # Calculate expiration
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )

        # Store in database
        refresh_token = RefreshToken(
            token=token_string,
            user_id=user_id,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        self.db.add(refresh_token)
        await self.db.commit()
        await self.db.refresh(refresh_token)

        return refresh_token

    async def rotate_refresh_token(
        self,
        old_token: RefreshToken,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> RefreshToken:
        """Rotate a refresh token (revoke old, create new).

        Args:
            old_token: Existing refresh token
            user_agent: Browser/user agent string
            ip_address: Client IP address

        Returns:
            RefreshToken: New refresh token
        """
        # Revoke old token
        old_token.revoked_at = datetime.now(timezone.utc)

        # Create new token
        return await self.create_refresh_token(
            user_id=old_token.user_id,
            user_agent=user_agent,
            ip_address=ip_address,
        )

    async def get_refresh_token(self, token_string: str) -> RefreshToken | None:
        """Get refresh token from database.

        Args:
            token_string: Token string

        Returns:
            RefreshToken | None: Token record or None
        """
        query = select(RefreshToken).where(
            and_(
                RefreshToken.token == token_string,
                RefreshToken.revoked_at == None,
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def verify_refresh_token(
        self,
        token_string: str,
    ) -> tuple[RefreshToken | None, str | None]:
        """Verify refresh token validity.

        Args:
            token_string: Token string

        Returns:
            tuple: (token_record, error_message)
        """
        # Get token from database
        token_record = await self.get_refresh_token(token_string)

        if token_record is None:
            return None, "Invalid refresh token"

        # Check expiration
        if token_record.expires_at < datetime.now(timezone.utc):
            return None, "Refresh token expired"

        # Decode JWT to verify signature
        payload = decode_token(token_string)
        if payload is None:
            return None, "Invalid token signature"

        # Verify user ID matches
        if payload.get("sub") != str(token_record.user_id):
            return None, "Token user mismatch"

        return token_record, None

    async def revoke_refresh_token(self, token: RefreshToken) -> None:
        """Revoke a refresh token.

        Args:
            token: Token to revoke
        """
        token.revoked_at = datetime.now(timezone.utc)
        await self.db.commit()

    async def revoke_user_tokens(
        self,
        user_id: str | uuid.UUID,
        exclude_token_id: str | uuid.UUID | None = None,
    ) -> int:
        """Revoke all refresh tokens for a user.

        Args:
            user_id: User ID
            exclude_token_id: Optional token ID to exclude from revocation

        Returns:
            int: Number of tokens revoked
        """
        conditions = [
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at == None,
        ]

        if exclude_token_id:
            conditions.append(RefreshToken.id != exclude_token_id)

        query = select(RefreshToken).where(and_(*conditions))
        result = await self.db.execute(query)
        tokens = result.scalars().all()

        count = 0
        for token in tokens:
            token.revoked_at = datetime.now(timezone.utc)
            count += 1

        await self.db.commit()
        return count

    async def get_user_sessions(
        self,
        user_id: str | uuid.UUID,
    ) -> list[RefreshToken]:
        """Get all active sessions for a user.

        Args:
            user_id: User ID

        Returns:
            list[RefreshToken]: List of active refresh tokens
        """
        query = select(RefreshToken).where(
            and_(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at == None,
                RefreshToken.expires_at > datetime.now(timezone.utc),
            )
        ).order_by(desc(RefreshToken.created_at))

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def cleanup_expired_tokens(self, days: int = 30) -> int:
        """Delete expired and revoked tokens older than specified days.

        Args:
            days: Number of days to retain

        Returns:
            int: Number of tokens deleted
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        # Find tokens to delete
        query = select(RefreshToken).where(
            and_(
                RefreshToken.expires_at < cutoff_date,
            )
        )
        result = await self.db.execute(query)
        tokens = result.scalars().all()

        count = len(tokens)
        for token in tokens:
            await self.db.delete(token)

        await self.db.commit()
        return count

    async def change_password(
        self,
        user_id: str | uuid.UUID,
        hashed_password: str,
        data: ChangePasswordRequest,
    ) -> bool:
        """Change user password.

        Args:
            user_id: User ID
            hashed_password: Current hashed password
            data: Password change data

        Returns:
            bool: True if password changed

        Raises:
            ValueError: If old password is incorrect
        """
        if not verify_password(data.old_password, hashed_password):
            raise ValueError("Incorrect password")

        # Hash new password
        new_hash = get_password_hash(data.new_password)

        # Update password
        from app.models.user import User

        query = select(User).where(User.id == user_id)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()

        if user:
            user.hashed_password = new_hash
            await self.db.commit()

            # Revoke all refresh tokens for security
            await self.revoke_user_tokens(user_id)

            return True

        return False
