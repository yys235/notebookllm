"""Add editor_type column to notes table.

Revision ID: 006
Revises: 005
Create Date: 2025-03-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add editor_type column to notes table."""
    # Add editor_type column with default 'docx'
    op.add_column(
        "notes",
        sa.Column(
            "editor_type",
            sa.String(50),
            nullable=False,
            server_default="docx",
        ),
    )

    # Create index for editor_type
    op.create_index("ix_notes_editor_type", "notes", ["editor_type"])


def downgrade() -> None:
    """Remove editor_type column from notes table."""
    op.drop_index("ix_notes_editor_type", table_name="notes")
    op.drop_column("notes", "editor_type")
