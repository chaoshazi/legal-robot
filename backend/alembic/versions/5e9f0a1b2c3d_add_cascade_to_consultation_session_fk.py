"""add cascade to consultation session fk

Revision ID: 5e9f0a1b2c3d
Revises: 4d8e9f0a1b2c
Create Date: 2026-05-01 15:00:00.000000
"""
from typing import Sequence, Union

from alembic import op

revision: str = "5e9f0a1b2c3d"
down_revision: Union[str, None] = "4d8e9f0a1b2c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("consultations_session_id_fkey", "consultations", type_="foreignkey")
    op.create_foreign_key(
        "consultations_session_id_fkey",
        "consultations",
        "sessions",
        ["session_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("consultations_session_id_fkey", "consultations", type_="foreignkey")
    op.create_foreign_key(
        "consultations_session_id_fkey",
        "consultations",
        "sessions",
        ["session_id"],
        ["id"],
    )
