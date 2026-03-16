"""Note-related schemas."""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, ConfigDict


# Note visibility type
VisibilityType = Literal["private", "public"]


class NoteBase(BaseModel):
    """Base note schema with common fields."""

    title: str = Field(..., min_length=1, max_length=500, description="Note title")
    content: str = Field(..., description="Note content in markdown format")


# Editor type
EditorType = Literal["docx", "docx-blocks", "feishu-docs", "excel", "mindmap", "flowchart"]


class NoteCreate(NoteBase):
    """Schema for creating a new note."""

    is_pinned: bool = Field(default=False, description="Pin note to top")
    visibility: VisibilityType = Field(default="private", description="Note visibility")
    category_id: str | None = Field(None, description="Category ID")
    editor_type: EditorType = Field(default="docx", description="Editor type")


class NoteUpdate(BaseModel):
    """Schema for updating a note."""

    title: str | None = Field(None, min_length=1, max_length=500)
    content: str | None = None
    is_pinned: bool | None = None
    visibility: VisibilityType | None = Field(None, description="Note visibility")
    category_id: str | None = None
    editor_type: EditorType | None = Field(None, description="Editor type")


class NoteRead(NoteBase):
    """Schema for note response."""

    id: str = Field(..., description="Note ID")
    user_id: str = Field(..., description="Owner user ID")
    is_pinned: bool = Field(default=False, description="Pin status")
    visibility: str = Field(default="private", description="Note visibility")
    category_id: str | None = Field(None, description="Category ID")
    editor_type: str = Field(default="docx", description="Editor type")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    @field_validator('id', 'user_id', 'category_id', mode='before')
    @classmethod
    def uuid_to_str(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v

    def model_dump(self, **kwargs):
        """Override to map snake_case to camelCase for frontend."""
        data = super().model_dump(**kwargs)
        if 'user_id' in data:
            data['userId'] = data.pop('user_id')
        if 'is_pinned' in data:
            data['isPinned'] = data.pop('is_pinned')
        if 'category_id' in data:
            data['categoryId'] = data.pop('category_id')
        if 'editor_type' in data:
            data['editorType'] = data.pop('editor_type')
        if 'created_at' in data:
            data['createdAt'] = data.pop('created_at')
        if 'updated_at' in data:
            data['updatedAt'] = data.pop('updated_at')
        return data

    model_config = ConfigDict(from_attributes=True)


class NoteSummary(BaseModel):
    """Schema for note summary in list view (excludes content)."""

    id: str = Field(..., description="Note ID")
    title: str = Field(..., description="Note title")
    is_pinned: bool = Field(default=False, description="Pin status")
    visibility: str = Field(default="private", description="Note visibility")
    category_id: str | None = Field(None, description="Category ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    # Preview field - will be serialized as 'content' for frontend compatibility
    preview: str = Field(..., description="First 200 chars of content")

    @field_validator('id', 'category_id', mode='before')
    @classmethod
    def uuid_to_str(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v

    def model_dump(self, **kwargs):
        """Override to map preview to content for frontend."""
        data = super().model_dump(**kwargs)
        # Map snake_case to camelCase for frontend
        if 'preview' in data:
            data['content'] = data.pop('preview')
        if 'is_pinned' in data:
            data['isPinned'] = data.pop('is_pinned')
        if 'category_id' in data:
            data['categoryId'] = data.pop('category_id')
        if 'created_at' in data:
            data['createdAt'] = data.pop('created_at')
        if 'updated_at' in data:
            data['updatedAt'] = data.pop('updated_at')
        return data

    model_config = ConfigDict(from_attributes=True)


class NoteVersionRead(BaseModel):
    """Schema for note version response."""

    id: str = Field(..., description="Version ID")
    note_id: str = Field(..., description="Note ID")
    title: str = Field(..., description="Title at this version")
    content: str = Field(..., description="Content at this version")
    version_number: int = Field(..., description="Version number")
    change_summary: str | None = Field(None, description="Change summary")
    created_at: datetime = Field(..., description="Version creation timestamp")

    @field_validator('id', 'note_id', mode='before')
    @classmethod
    def uuid_to_str(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v

    model_config = {"from_attributes": True}


class NoteRestoreRequest(BaseModel):
    """Schema for restoring a note from version history."""

    version_id: str = Field(..., description="Version ID to restore from")


class NoteAttachmentRead(BaseModel):
    """Schema for note attachment response."""

    id: str = Field(..., description="Attachment ID")
    note_id: str = Field(..., description="Note ID")
    filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    mime_type: str | None = Field(None, description="MIME type")
    created_at: datetime = Field(..., description="Upload timestamp")

    @field_validator('id', 'note_id', mode='before')
    @classmethod
    def uuid_to_str(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v

    model_config = {"from_attributes": True}


class BatchDeleteRequest(BaseModel):
    """Schema for batch deleting notes."""

    note_ids: list[str] = Field(..., min_length=1, max_length=50, description="Note IDs to delete")


class BatchUpdateRequest(BaseModel):
    """Schema for batch updating notes."""

    note_ids: list[str] = Field(..., min_length=1, max_length=50, description="Note IDs to update")
    is_pinned: bool | None = Field(None, description="New pin status")
    category_id: str | None = Field(None, description="New category ID")
