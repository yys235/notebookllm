"""Note block schemas for block-based editor."""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, ConfigDict

# BlockType enum matching frontend BlockType definition
# Based on: frontend/src/plugins/feishu-docs/types.ts
BlockType = Literal[
    # Text blocks
    "text",  # Plain text paragraph
    "h1",  # Heading 1
    "h2",  # Heading 2
    "h3",  # Heading 3
    "h4",  # Heading 4
    "h5",  # Heading 5
    "h6",  # Heading 6
    "quote",  # Quote block
    "code",  # Code block
    "callout",  # Callout/highlight box
    # List blocks
    "bulletList",  # Unordered list container
    "orderedList",  # Ordered list container
    "taskList",  # Task list container
    "listItem",  # List item
    "taskItem",  # Task item
    # Media blocks
    "image",  # Image
    "video",  # Video
    "file",  # File attachment
    # Structure blocks
    "divider",  # Horizontal divider
    "table",  # Table
    "grid",  # Grid/column layout
    # Special blocks
    "toggle",  # Collapsible toggle block
]


class BlockBase(BaseModel):
    """Base block schema with common fields."""

    block_type: BlockType = Field(..., description="Block type")
    content: str | None = Field(None, description="Block content (JSON string)")
    properties: dict | None = Field(None, description="Block attributes/metadata")
    parent_block_id: str | None = Field(None, description="Parent block ID for nested blocks")
    sort_order: int = Field(..., ge=0, description="Position in the document")


class BlockCreate(BaseModel):
    """Schema for creating a new block."""

    block_type: BlockType = Field(..., alias="type", description="Block type")
    content: str | None = Field(None, description="Block content (JSON string)")
    properties: dict | None = Field(None, alias="attrs", description="Block attributes/metadata")
    parent_block_id: str | None = Field(None, alias="parentId", description="Parent block ID")
    sort_order: int | None = Field(None, ge=0, alias="position", description="Position in the document")

    model_config = ConfigDict(populate_by_name=True)


class BlockUpdate(BaseModel):
    """Schema for updating a block."""

    block_type: BlockType | None = Field(None, alias="type", description="Block type")
    content: str | None = Field(None, description="Block content")
    properties: dict | None = Field(None, alias="attrs", description="Block attributes")
    parent_block_id: str | None = Field(None, alias="parentId", description="Parent block ID")
    sort_order: int | None = Field(None, ge=0, alias="position", description="Position in document")

    model_config = ConfigDict(populate_by_name=True)


class BlockResponse(BaseModel):
    """Schema for block response."""

    id: str = Field(..., description="Block ID")
    note_id: str = Field(..., description="Note ID this block belongs to")
    block_type: BlockType = Field(..., description="Block type")
    content: str | None = Field(None, description="Block content")
    properties: dict | None = Field(None, description="Block attributes/metadata")
    parent_block_id: str | None = Field(None, description="Parent block ID")
    sort_order: int = Field(..., description="Position in document")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    @field_validator("id", "note_id", "parent_block_id", mode="before")
    @classmethod
    def uuid_to_str(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v

    def model_dump(self, **kwargs):
        """Override to map snake_case to camelCase for frontend."""
        data = super().model_dump(**kwargs)
        # Map to frontend-friendly names
        if "block_type" in data:
            data["type"] = data.pop("block_type")
        if "properties" in data:
            data["attrs"] = data.pop("properties")
        if "parent_block_id" in data:
            data["parentId"] = data.pop("parent_block_id")
        if "sort_order" in data:
            data["position"] = data.pop("sort_order")
        if "note_id" in data:
            data["noteId"] = data.pop("note_id")
        if "created_at" in data:
            data["createdAt"] = data.pop("created_at")
        if "updated_at" in data:
            data["updatedAt"] = data.pop("updated_at")
        return data

    model_config = ConfigDict(from_attributes=True)


class BlockListResponse(BaseModel):
    """Schema for list of blocks response."""

    blocks: list[BlockResponse] = Field(..., description="List of blocks")
    total: int = Field(..., description="Total number of blocks")

    def model_dump(self, **kwargs):
        """Override to ensure nested blocks also use correct format."""
        data = super().model_dump(**kwargs)
        if "blocks" in data:
            data["blocks"] = [
                block.model_dump(**kwargs) if hasattr(block, "model_dump") else block
                for block in data["blocks"]
            ]
        return data


class ReorderRequest(BaseModel):
    """Schema for reordering blocks."""

    block_orders: list[dict[str, int | str]] = Field(
        ...,
        description="List of {block_id, position} mappings for new order",
        examples=[[{"block_id": "uuid", "position": 0}]],
    )

    @field_validator("block_orders")
    @classmethod
    def validate_block_orders(cls, v):
        """Validate that block_orders is not empty and has valid structure."""
        if not v:
            raise ValueError("block_orders cannot be empty")
        for item in v:
            if "block_id" not in item:
                raise ValueError("Each item must have a block_id")
            if "position" not in item:
                raise ValueError("Each item must have a position")
            if not isinstance(item["position"], int) or item["position"] < 0:
                raise ValueError("position must be a non-negative integer")
        return v
