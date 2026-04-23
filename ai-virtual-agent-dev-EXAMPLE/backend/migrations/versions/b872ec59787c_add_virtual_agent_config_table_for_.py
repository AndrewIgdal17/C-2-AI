"""add virtual agent config table for responses api

Revision ID: b872ec59787c
Revises: f6a1b2c3d4e5
Create Date: 2025-09-12 09:44:22.880561

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b872ec59787c'
down_revision: Union[str, None] = 'f6a1b2c3d4e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add virtual_agent_configs table for Responses API support."""
    op.create_table('virtual_agent_configs',
                    sa.Column('id', sa.String(length=255), nullable=False),
                    sa.Column('name', sa.String(length=255), nullable=False),
                    sa.Column('model_name', sa.String(length=255), nullable=False),
                    sa.Column('prompt', sa.String(), nullable=True),
                    sa.Column('tools', sa.JSON(), nullable=True),
                    sa.Column('knowledge_base_ids', sa.JSON(), nullable=True),
                    sa.Column('input_shields', sa.JSON(), nullable=True),
                    sa.Column('output_shields', sa.JSON(), nullable=True),
                    sa.Column('sampling_strategy', sa.String(length=50), nullable=True),
                    sa.Column('temperature', sa.JSON(), nullable=True),
                    sa.Column('top_p', sa.JSON(), nullable=True),
                    sa.Column('top_k', sa.JSON(), nullable=True),
                    sa.Column('max_tokens', sa.JSON(), nullable=True),
                    sa.Column('repetition_penalty', sa.JSON(), nullable=True),
                    sa.Column('max_infer_iters', sa.JSON(), nullable=True),
                    sa.Column('created_at', sa.TIMESTAMP(timezone=True),
                              server_default=sa.text('now()'), nullable=True),
                    sa.Column('updated_at', sa.TIMESTAMP(timezone=True),
                              server_default=sa.text('now()'), nullable=True),
                    sa.PrimaryKeyConstraint('id')
                    )


def downgrade() -> None:
    """Remove virtual_agent_configs table."""
    op.drop_table('virtual_agent_configs')
