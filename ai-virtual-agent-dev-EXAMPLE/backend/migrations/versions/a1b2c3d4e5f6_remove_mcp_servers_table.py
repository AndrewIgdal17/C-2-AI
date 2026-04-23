"""remove mcp_servers table

Revision ID: a1b2c3d4e5f6
Revises: ff341a7acadb
Create Date: 2025-01-26 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "ff341a7acadb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - remove mcp_servers table as MCP servers
    are now managed directly in LlamaStack."""
    # Drop the mcp_servers table
    op.drop_table("mcp_servers")


def downgrade() -> None:
    """Downgrade schema - recreate mcp_servers table."""
    # Recreate the mcp_servers table if we need to roll back
    op.create_table(
        "mcp_servers",
        sa.Column("toolgroup_id", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("endpoint_url", sa.String(length=255), nullable=False),
        sa.Column("configuration", sa.JSON(), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("toolgroup_id"),
    )
