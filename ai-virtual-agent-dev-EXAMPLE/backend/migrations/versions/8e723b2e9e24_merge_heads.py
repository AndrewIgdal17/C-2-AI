"""merge heads

Revision ID: 8e723b2e9e24
Revises: a1b2c3d4e5f6, aa111bb2cc33
Create Date: 2025-07-23 14:10:40.201157

"""

from typing import Sequence, Union

# No operations needed for merge heads


# revision identifiers, used by Alembic.
revision: str = "8e723b2e9e24"
down_revision: Union[str, None] = ("a1b2c3d4e5f6", "aa111bb2cc33")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
