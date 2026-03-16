"""Note block management routes for block-based editor."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logger import get_logger
from app.dependencies import CurrentUser
from app.schemas.note_block import (
    BlockCreate,
    BlockListResponse,
    BlockResponse,
    BlockUpdate,
    ReorderRequest,
)

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


@router.get("/notes/{note_id}/blocks", response_model=BlockListResponse)
async def list_blocks(
    note_id: str,
    current_user: CurrentUser,
    db: DBSession,
    parent_id: str | None = Query(None, description="Filter by parent block ID"),
):
    """List all blocks for a note.

    Supports filtering by parent_id to get nested blocks.
    Returns blocks ordered by sort_order.
    """
    from app.models.note import Note
    from app.models.note_block import NoteBlock
    from sqlalchemy import and_, select

    # Validate note ID format
    validate_uuid(note_id, "note_id")

    # Verify note exists and belongs to user
    note_query = select(Note).where(
        and_(
            Note.id == note_id,
            Note.user_id == current_user.id,
            Note.is_deleted == False,
        )
    )
    note_result = await db.execute(note_query)
    note = note_result.scalar_one_or_none()

    if note is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found",
        )

    # Query blocks
    conditions = [NoteBlock.note_id == note_id]
    if parent_id:
        validate_uuid(parent_id, "parent_id")
        conditions.append(NoteBlock.parent_block_id == parent_id)

    blocks_query = (
        select(NoteBlock)
        .where(*conditions)
        .order_by(NoteBlock.sort_order)
    )
    result = await db.execute(blocks_query)
    blocks = result.scalars().all()

    # Convert to response schemas
    block_responses = [BlockResponse.model_validate(block) for block in blocks]

    return BlockListResponse(blocks=block_responses, total=len(block_responses))


@router.post("/notes/{note_id}/blocks", response_model=BlockResponse, status_code=status.HTTP_201_CREATED)
async def create_block(
    note_id: str,
    data: BlockCreate,
    current_user: CurrentUser,
    db: DBSession,
):
    """Create a new block for a note.

    Automatically assigns the next available sort_order if not specified.
    """
    from app.models.note import Note
    from app.models.note_block import NoteBlock
    from sqlalchemy import and_, func, select
    import uuid

    # Validate note ID format
    validate_uuid(note_id, "note_id")

    # Verify note exists and belongs to user
    note_query = select(Note).where(
        and_(
            Note.id == note_id,
            Note.user_id == current_user.id,
            Note.is_deleted == False,
        )
    )
    note_result = await db.execute(note_query)
    note = note_result.scalar_one_or_none()

    if note is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found",
        )

    # Validate parent_block_id if provided
    parent_block_id = data.parent_block_id
    if parent_block_id:
        validate_uuid(parent_block_id, "parent_block_id")
        # Verify parent block exists and belongs to the same note
        parent_query = select(NoteBlock).where(
            and_(
                NoteBlock.id == parent_block_id,
                NoteBlock.note_id == note_id,
            )
        )
        parent_result = await db.execute(parent_query)
        parent = parent_result.scalar_one_or_none()
        if parent is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parent block not found",
            )

    # Get next sort_order if not provided
    sort_order = data.sort_order
    if sort_order is None:
        max_pos_query = (
            select(func.max(NoteBlock.sort_order))
            .where(NoteBlock.note_id == note_id)
        )
        if parent_block_id:
            max_pos_query = max_pos_query.where(NoteBlock.parent_block_id == parent_block_id)
        max_pos_result = await db.execute(max_pos_query)
        max_position = max_pos_result.scalar() or -1
        sort_order = max_position + 1

    # Create block
    block = NoteBlock(
        id=uuid.uuid4(),
        note_id=note_id,
        block_type=data.block_type,
        content=data.content,
        properties=data.properties,
        parent_block_id=parent_block_id,
        sort_order=sort_order,
    )

    db.add(block)
    await db.commit()
    await db.refresh(block)

    logger.info(
        "Block created",
        user_id=str(current_user.id),
        note_id=str(note_id),
        block_id=str(block.id),
    )

    return BlockResponse.model_validate(block)


@router.put("/blocks/{block_id}", response_model=BlockResponse)
async def update_block(
    block_id: str,
    data: BlockUpdate,
    current_user: CurrentUser,
    db: DBSession,
):
    """Update a block.

    Can update block_type, content, properties, parent_block_id, and sort_order.
    """
    from app.models.note import Note
    from app.models.note_block import NoteBlock
    from sqlalchemy import and_, select

    # Validate block ID format
    validate_uuid(block_id, "block_id")

    # Get block and verify ownership through note
    block_query = (
        select(NoteBlock)
        .join(Note, NoteBlock.note_id == Note.id)
        .where(
            and_(
                NoteBlock.id == block_id,
                Note.user_id == current_user.id,
                Note.is_deleted == False,
            )
        )
    )
    block_result = await db.execute(block_query)
    block = block_result.scalar_one_or_none()

    if block is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Block not found",
        )

    # Update fields
    if data.block_type is not None:
        block.block_type = data.block_type
    if data.content is not None:
        block.content = data.content
    if data.properties is not None:
        block.properties = data.properties
    if data.parent_block_id is not None:
        if data.parent_block_id:  # Validate non-empty parent_block_id
            validate_uuid(data.parent_block_id, "parent_block_id")
            # Verify parent block exists and belongs to the same note
            parent_query = select(NoteBlock).where(
                and_(
                    NoteBlock.id == data.parent_block_id,
                    NoteBlock.note_id == block.note_id,
                    NoteBlock.id != block_id,  # Prevent self-reference
                )
            )
            parent_result = await db.execute(parent_query)
            parent = parent_result.scalar_one_or_none()
            if parent is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Parent block not found",
                )
        block.parent_block_id = data.parent_block_id if data.parent_block_id else None
    if data.sort_order is not None:
        block.sort_order = data.sort_order

    await db.commit()
    await db.refresh(block)

    logger.info(
        "Block updated",
        user_id=str(current_user.id),
        block_id=str(block_id),
    )

    return BlockResponse.model_validate(block)


@router.delete("/blocks/{block_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_block(
    block_id: str,
    current_user: CurrentUser,
    db: DBSession,
):
    """Delete a block.

    Also deletes all child blocks recursively via cascade.
    """
    from app.models.note import Note
    from app.models.note_block import NoteBlock
    from sqlalchemy import and_, delete, select

    # Validate block ID format
    validate_uuid(block_id, "block_id")

    # Get block and verify ownership through note
    block_query = (
        select(NoteBlock)
        .join(Note, NoteBlock.note_id == Note.id)
        .where(
            and_(
                NoteBlock.id == block_id,
                Note.user_id == current_user.id,
                Note.is_deleted == False,
            )
        )
    )
    block_result = await db.execute(block_query)
    block = block_result.scalar_one_or_none()

    if block is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Block not found",
        )

    # Delete the block (cascade delete will handle children via foreign key)
    await db.execute(delete(NoteBlock).where(NoteBlock.id == block_id))
    await db.commit()

    logger.info(
        "Block deleted",
        user_id=str(current_user.id),
        block_id=str(block_id),
    )


@router.post("/notes/{note_id}/blocks/reorder", status_code=status.HTTP_204_NO_CONTENT)
async def reorder_blocks(
    note_id: str,
    data: ReorderRequest,
    current_user: CurrentUser,
    db: DBSession,
):
    """Reorder blocks within a note.

    Accepts a list of {block_id, position} mappings to update block sort_order.
    This is useful for drag-and-drop reordering functionality.
    """
    from app.models.note import Note
    from app.models.note_block import NoteBlock
    from sqlalchemy import and_, select

    # Validate note ID format
    validate_uuid(note_id, "note_id")

    # Verify note exists and belongs to user
    note_query = select(Note).where(
        and_(
            Note.id == note_id,
            Note.user_id == current_user.id,
            Note.is_deleted == False,
        )
    )
    note_result = await db.execute(note_query)
    note = note_result.scalar_one_or_none()

    if note is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found",
        )

    # Get all block IDs to update
    block_ids = [item["block_id"] for item in data.block_orders]

    # Fetch all blocks in a single query
    blocks_query = select(NoteBlock).where(
        and_(
            NoteBlock.note_id == note_id,
            NoteBlock.id.in_(block_ids),
        )
    )
    blocks_result = await db.execute(blocks_query)
    blocks = {str(block.id): block for block in blocks_result.scalars().all()}

    # Update sort_order
    for item in data.block_orders:
        block_id = item["block_id"]
        if block_id not in blocks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Block {block_id} not found in note",
            )
        blocks[block_id].sort_order = int(item["position"])

    await db.commit()

    logger.info(
        "Blocks reordered",
        user_id=str(current_user.id),
        note_id=str(note_id),
        count=len(data.block_orders),
    )
