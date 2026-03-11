"""User business logic service."""
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, and_, or_

from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


class UserService:
    """Service for user-related operations."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize user service.

        Args:
            db: Database session
        """
        self.db = db

    async def get_by_id(self, user_id: str | uuid.UUID) -> User | None:
        """Get user by ID.

        Args:
            user_id: User ID

        Returns:
            User | None: User instance or None
        """
        query = select(User).where(User.id == user_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email.

        Args:
            email: User email

        Returns:
            User | None: User instance or None
        """
        query = select(User).where(User.email == email)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        """Get user by username.

        Args:
            username: Username

        Returns:
            User | None: User instance or None
        """
        query = select(User).where(User.username == username)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def authenticate(self, username: str, password: str) -> User | None:
        """Authenticate user with username/email and password.

        Args:
            username: Username or email
            password: Plain password

        Returns:
            User | None: Authenticated user or None
        """
        # Try to find user by username or email
        query = select(User).where(
            or_(
                User.username == username,
                User.email == username,
            )
        )
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()

        if user is None:
            return None

        if not verify_password(password, user.hashed_password):
            return None

        # Update last login
        user.last_login_at = datetime.now(timezone.utc)
        await self.db.commit()

        return user

    async def create(self, data: UserCreate) -> User:
        """Create a new user.

        Args:
            data: User creation data

        Returns:
            User: Created user

        Raises:
            ValueError: If email or username already exists
        """
        # Check for existing user
        existing = await self.get_by_email(data.email)
        if existing:
            raise ValueError("Email already registered")

        existing = await self.get_by_username(data.username)
        if existing:
            raise ValueError("Username already taken")

        # Create user
        user = User(
            email=data.email,
            username=data.username,
            hashed_password=get_password_hash(data.password),
            full_name=data.full_name,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def update(self, user: User, data: UserUpdate) -> User:
        """Update user information.

        Args:
            user: User instance to update
            data: Update data

        Returns:
            User: Updated user

        Raises:
            ValueError: If email or username conflict
        """
        update_data = data.model_dump(exclude_unset=True)

        # Handle password update
        if "password" in update_data:
            update_data["hashed_password"] = get_password_hash(update_data.pop("password"))

        # Check for conflicts
        if "email" in update_data and update_data["email"] != user.email:
            existing = await self.get_by_email(update_data["email"])
            if existing:
                raise ValueError("Email already registered")

        if "username" in update_data and update_data["username"] != user.username:
            existing = await self.get_by_username(update_data["username"])
            if existing:
                raise ValueError("Username already taken")

        # Apply updates
        for field, value in update_data.items():
            setattr(user, field, value)

        await self.db.commit()
        await self.db.refresh(user)
        return user
