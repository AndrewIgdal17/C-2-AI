"""remove_agent_types_table

Revision ID: d52f80e39bc4
Revises: b872ec59787c
Create Date: 2025-09-12 14:44:59.208736

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd52f80e39bc4'
down_revision: Union[str, None] = 'b872ec59787c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop the agent_types table
    op.drop_table('agent_types')

    # Drop the enum type
    op.execute("DROP TYPE IF EXISTS agent_type_enum")


def downgrade() -> None:
    """Downgrade schema."""
    # Recreate the enum type
    op.execute("CREATE TYPE agent_type_enum AS ENUM ('REGULAR', 'REACT')")

    # Recreate the agent_types table
    op.create_table(
        'agent_types',
        sa.Column('agent_id', sa.String(length=255), nullable=False),
        sa.Column(
            'agent_type',
            sa.Enum('REGULAR', 'REACT', name='agent_type_enum'),
            nullable=False,
        ),
        sa.Column(
            'created_at',
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text('now()'),
            nullable=True,
        ),
        sa.Column(
            'updated_at',
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text('now()'),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint('agent_id'),
    )
