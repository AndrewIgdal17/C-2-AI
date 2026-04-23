"""Drop chat_messages table

Revision ID: 1b936f86b868
Revises: 8b71c25a7317
Create Date: 2025-11-10 12:24:42.510505

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '1b936f86b868'
down_revision: Union[str, None] = '8b71c25a7317'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop chat_messages table - messages are now managed by LlamaStack
    op.drop_table('chat_messages')


def downgrade() -> None:
    """Downgrade schema."""
    # Not supporting downgrade - would need to recreate chat_messages table
    # and migrate data from LlamaStack, which is not practical
    pass
