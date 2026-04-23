"""Convert user agent_ids from JSON to UUID array

Revision ID: 7998698b6e6b
Revises: 8c7db47f5668
Create Date: 2025-10-01 10:13:59.757977

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, ARRAY


# revision identifiers, used by Alembic.
revision: str = '7998698b6e6b'
down_revision: Union[str, None] = '8c7db47f5668'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add a temporary column for UUID array
    op.add_column('users', sa.Column('agent_ids_temp', ARRAY(UUID(as_uuid=True)), nullable=True))

    # Convert JSON agent_ids to UUID array
    # This SQL safely converts JSON array of strings to UUID array
    op.execute("""
        UPDATE users
        SET agent_ids_temp = ARRAY(
            SELECT (json_array_elements_text(agent_ids))::uuid
            FROM (SELECT agent_ids) AS sub
        )
        WHERE agent_ids IS NOT NULL
        AND json_array_length(agent_ids) > 0
    """)

    # Set empty arrays for users with empty JSON arrays
    op.execute("""
        UPDATE users
        SET agent_ids_temp = ARRAY[]::uuid[]
        WHERE agent_ids IS NOT NULL
        AND (json_array_length(agent_ids) = 0 OR agent_ids::text = '[]')
    """)

    # Handle NULL cases
    op.execute("""
        UPDATE users
        SET agent_ids_temp = ARRAY[]::uuid[]
        WHERE agent_ids IS NULL
    """)

    # Drop the old JSON column
    op.drop_column('users', 'agent_ids')

    # Rename the temp column to agent_ids
    op.alter_column('users', 'agent_ids_temp', new_column_name='agent_ids')

    # Make the column NOT NULL with default empty array
    op.alter_column('users', 'agent_ids', nullable=False, server_default='{}')


def downgrade() -> None:
    """Downgrade schema."""
    # Add temporary JSON column
    op.add_column('users', sa.Column('agent_ids_temp', sa.JSON, nullable=True))

    # Convert UUID array back to JSON
    op.execute("""
        UPDATE users
        SET agent_ids_temp = array_to_json(agent_ids)
        WHERE agent_ids IS NOT NULL
    """)

    # Handle NULL cases
    op.execute("""
        UPDATE users
        SET agent_ids_temp = '[]'::json
        WHERE agent_ids IS NULL
    """)

    # Drop the UUID array column
    op.drop_column('users', 'agent_ids')

    # Rename temp column back to agent_ids
    op.alter_column('users', 'agent_ids_temp', new_column_name='agent_ids')

    # Make it NOT NULL with default empty list
    op.alter_column('users', 'agent_ids', nullable=False, server_default="'[]'::json")
