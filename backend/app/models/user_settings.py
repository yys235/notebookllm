"""User settings model for storing user preferences."""
from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class UserSettings(Base):
    """User settings and preferences."""

    __tablename__ = "user_settings"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # AI Settings
    ai_provider = Column(String(50), default="ollama")
    ai_api_key = Column(String(255), nullable=True)
    ai_base_url = Column(String(500), default="http://192.168.123.220:11434")
    ai_model = Column(String(100), nullable=True)
    ai_temperature = Column(String(10), default="0.7")
    ai_max_tokens = Column(String(10), default="2000")
    ai_enable_rag = Column(String(10), default="true")

    # Embedding Settings
    embedding_provider = Column(String(50), default="ollama")
    embedding_api_key = Column(String(255), nullable=True)
    embedding_base_url = Column(String(500), default="http://192.168.123.220:11434")
    embedding_model = Column(String(100), nullable=True)

    # Appearance Settings
    theme = Column(String(20), default="light")
    font_size = Column(String(20), default="medium")
    editor_mode = Column(String(20), default="rich")

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    user = relationship("User", backref="settings")
