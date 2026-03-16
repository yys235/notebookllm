"""Add note blocks table for block-based editor.

Revision ID: 005
Revises: 004
Create Date: 2025-03-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create note_blocks table for block-based content storage."""

    # ========================================
    # Note blocks table
    # ========================================
    op.create_table(
        "note_blocks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "note_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("notes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("block_type", sa.String(50), nullable=False),
        sa.Column("content", sa.Text()),
        sa.Column("properties", postgresql.JSONB()),
        sa.Column("sort_order", sa.Integer(), default=0, nullable=False),
        sa.Column(
            "parent_block_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("note_blocks.id", ondelete="CASCADE"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index("ix_note_blocks_note_id", "note_blocks", ["note_id"])
    op.create_index("ix_note_blocks_parent_block_id", "note_blocks", ["parent_block_id"])
    op.create_index("ix_note_blocks_sort_order", "note_blocks", ["sort_order"])

    # ========================================
    # Trigger: Auto-update updated_at timestamp
    # ========================================
    # Apply trigger to note_blocks table
    op.execute(
        """
        CREATE TRIGGER note_blocks_updated_at
        BEFORE UPDATE ON note_blocks
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at()
        """
    )


def downgrade() -> None:
    """Drop note_blocks table."""

    # Drop trigger
    op.execute("DROP TRIGGER IF EXISTS note_blocks_updated_at ON note_blocks")

    # Drop indexes
    op.drop_index("ix_note_blocks_sort_order", table_name="note_blocks")
    op.drop_index("ix_note_blocks_parent_block_id", table_name="note_blocks")
    op.drop_index("ix_note_blocks_note_id", table_name="note_blocks")

    # Drop table
    op.drop_table("note_blocks")
