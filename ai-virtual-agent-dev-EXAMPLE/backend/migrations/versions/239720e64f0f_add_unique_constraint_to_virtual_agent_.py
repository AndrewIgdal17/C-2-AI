"""add unique constraint to virtual agent name

Revision ID: 239720e64f0f
Revises: 2ec52d890cf7
Create Date: 2025-09-30 10:52:47.026566

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '239720e64f0f'
down_revision: Union[str, None] = '2ec52d890cf7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add unique constraint to virtual_agents.name column
    op.create_unique_constraint(
        'uq_virtual_agents_name',
        'virtual_agents',
        ['name']
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove unique constraint from virtual_agents.name column
    op.drop_constraint(
        'uq_virtual_agents_name',
        'virtual_agents',
        type_='unique'
    )
