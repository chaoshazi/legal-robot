"""add mcp_servers table

Revision ID: 2a7b3c4d5e6f
Revises: 1a92189d5ca3
Create Date: 2026-05-01 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '2a7b3c4d5e6f'
down_revision: Union[str, Sequence[str], None] = '1a92189d5ca3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('mcp_servers',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('transport', sa.String(length=20), nullable=False, server_default='stdio'),
        sa.Column('command', sa.String(length=500), nullable=True),
        sa.Column('args', sa.Text(), nullable=True),
        sa.Column('url', sa.String(length=500), nullable=True),
        sa.Column('api_key', sa.String(length=500), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='disconnected'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('mcp_servers')
