"""create tools table

Revision ID: 4d8e9f0a1b2c
Revises: 3c8d9e0f1a2b
Create Date: 2026-05-01 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "4d8e9f0a1b2c"
down_revision: Union[str, None] = "3c8d9e0f1a2b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tools",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("function_name", sa.String(100), nullable=False),
        sa.Column("parameters", sa.Text, nullable=True),
        sa.Column("tool_type", sa.String(20), nullable=False, server_default="builtin"),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Seed built-in tools
    op.execute(
        sa.text("""
            INSERT INTO tools (id, name, description, function_name, parameters, tool_type, enabled)
            VALUES
            ('a0000000-0000-0000-0000-000000000001', '法律检索', '检索中国法律法规条文，返回匹配的法律名称和条款号', 'search_laws', NULL, 'builtin', true),
            ('a0000000-0000-0000-0000-000000000002', '案例检索', '检索指导性案例，返回案例摘要', 'search_cases', NULL, 'builtin', true),
            ('a0000000-0000-0000-0000-000000000003', '赔偿计算', '根据劳动法计算工伤赔偿金额', 'calculate_compensation', '{"type":"object","properties":{"injury_type":{"type":"string"},"monthly_salary":{"type":"number"},"work_years":{"type":"integer"}}}', 'builtin', true)
        """)
    )


def downgrade() -> None:
    op.drop_table("tools")
