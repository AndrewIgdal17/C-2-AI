"""rename_virtual_agent_configs_to_virtual_agents

Revision ID: 2ec52d890cf7
Revises: f8715b450aec
Create Date: 2025-09-29 14:05:07.930797

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '2ec52d890cf7'
down_revision: Union[str, None] = 'f8715b450aec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Rename table from virtual_agent_configs to virtual_agents
    op.rename_table('virtual_agent_configs', 'virtual_agents')

    # Update foreign key constraints to reference the new table name
    # Drop old constraint and create new one
    op.drop_constraint('chat_sessions_agent_id_fkey', 'chat_sessions', type_='foreignkey')
    op.create_foreign_key(
        'chat_sessions_agent_id_fkey',
        'chat_sessions',
        'virtual_agents',
        ['agent_id'],
        ['id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop new constraint and create old one
    op.drop_constraint('chat_sessions_agent_id_fkey', 'chat_sessions', type_='foreignkey')
    op.create_foreign_key(
        'chat_sessions_agent_id_fkey',
        'chat_sessions',
        'virtual_agent_configs',
        ['agent_id'],
        ['id'],
        ondelete='CASCADE'
    )

    # Rename table back from virtual_agents to virtual_agent_configs
    op.rename_table('virtual_agents', 'virtual_agent_configs')
