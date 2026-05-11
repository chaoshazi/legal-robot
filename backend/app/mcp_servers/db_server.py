"""MCP server — database query tool for the legal consultation LLM agent.

Connects to PostgreSQL and exposes read-only database tools via MCP stdio transport.
The LLM agent (via LangChain) invokes these tools to retrieve structured data.

Run as a standalone process (stdio transport):
    python -m app.mcp_servers.db_server
"""

import json
import os
import sys
from typing import Any

# Ensure the backend root is on sys.path so we can import app config
_backend_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)

from mcp.server.fastmcp import FastMCP
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

server = FastMCP(
    name="legal-db-server",
    instructions="查询法律咨询系统数据库，获取用户、会话、咨询单等业务数据。",
)


# ── Database connection ────────────────────────────────────────────────────


def _get_dsn() -> str:
    """Read database DSN from environment (same .env the backend uses)."""
    user = os.getenv("POSTGRES_USER", "legalbot")
    password = os.getenv("POSTGRES_PASSWORD", "change_me_in_prod")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "legalbot")
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"


def _get_engine():
    dsn = _get_dsn()
    return create_async_engine(dsn, pool_pre_ping=True)


# ── Helpers ────────────────────────────────────────────────────────────────


def _row_to_dict(row: Any) -> dict:
    return {k: str(v) if hasattr(v, "isoformat") else v for k, v in dict(row._mapping).items()}


async def _execute_sql(sql: str) -> str:
    """Execute a SQL query and return results as formatted JSON."""
    engine = _get_engine()
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text(sql))
            rows = result.fetchall()
            if not rows:
                return json.dumps({"rows": [], "row_count": 0}, ensure_ascii=False, indent=2)
            columns = list(result.keys())
            data = [_row_to_dict(row) for row in rows]
            return json.dumps(
                {"columns": columns, "rows": data, "row_count": len(data)},
                ensure_ascii=False,
                indent=2,
            )
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        await engine.dispose()


# ── Tools ──────────────────────────────────────────────────────────────────


@server.tool()
async def query_database(sql: str) -> str:
    """执行 SQL 查询语句并返回结构化 JSON 结果。

    仅限 SELECT 查询，禁止修改数据库。返回格式包含 columns、rows、row_count。
    适用于查询用户信息、会话记录、咨询单、问答历史等业务数据。

    Args:
        sql: 完整的 SELECT SQL 查询语句。
    """
    sql_stripped = sql.strip().lower()
    if not sql_stripped.startswith("select"):
        return json.dumps({"error": "只允许 SELECT 查询"}, ensure_ascii=False)
    return await _execute_sql(sql)


@server.tool()
async def list_tables() -> str:
    """列出数据库中所有业务表及其行数统计。"""
    sql = """
        SELECT
            relname AS table_name,
            n_live_tup AS row_count
        FROM pg_stat_user_tables
        ORDER BY relname
    """
    return await _execute_sql(sql)


@server.tool()
async def get_table_schema(table_name: str) -> str:
    """获取指定数据库表的字段名、类型、是否可为空、默认值等 schema 信息。

    Args:
        table_name: 表名（如 users、sessions、messages、consultations 等）。
    """
    sql = f"""
        SELECT
            c.column_name,
            c.data_type,
            c.is_nullable,
            c.column_default,
            tc.constraint_type
        FROM information_schema.columns c
        LEFT JOIN information_schema.key_column_usage kcu
            ON c.table_name = kcu.table_name AND c.column_name = kcu.column_name
        LEFT JOIN information_schema.table_constraints tc
            ON kcu.constraint_name = tc.constraint_name
            AND tc.table_name = c.table_name
        WHERE c.table_name = '{table_name}'
        ORDER BY c.ordinal_position
    """
    return await _execute_sql(sql)


# ── Entrypoint ─────────────────────────────────────────────────────────────


def main():
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
