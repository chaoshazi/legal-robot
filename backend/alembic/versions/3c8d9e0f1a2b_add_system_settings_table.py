"""add system_settings table

Revision ID: 3c8d9e0f1a2b
Revises: 2a7b3c4d5e6f
Create Date: 2026-05-01 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3c8d9e0f1a2b'
down_revision: Union[str, Sequence[str], None] = '2a7b3c4d5e6f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('system_settings',
        sa.Column('key', sa.String(length=100), nullable=False),
        sa.Column('value', sa.Text(), nullable=False, server_default=''),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('key')
    )


def downgrade() -> None:
    op.drop_table('system_settings')
