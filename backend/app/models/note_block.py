"""Note block ORM model for block-based editor."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class NoteBlock(Base):
    """Note block model for block-based content storage."""

    __tablename__ = "note_blocks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    note_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("notes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    block_type: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str | None] = mapped_column(Text)
    properties: Mapped[dict | None] = mapped_column(JSONB)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True)
    parent_block_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("note_blocks.id", ondelete="CASCADE"),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    note: Mapped["Note"] = relationship(
        "Note", back_populates="blocks"
    )
    parent_block: Mapped["NoteBlock"] = relationship(
        "NoteBlock",
        remote_side=[id],
        back_populates="child_blocks"
    )
    child_blocks: Mapped[list["NoteBlock"]] = relationship(
        "NoteBlock",
        back_populates="parent_block",
        cascade="all, delete-orphan"
    )
