import uuid

from fastapi import APIRouter, Depends, status
from fastapi.exceptions import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.core.database import get_db
from app.models.mcp_server import MCPServer
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.mcp import MCPServerCreate, MCPServerInfo, MCPServerUpdate
from app.services.audit import log_audit

router = APIRouter()


@router.get("/servers")
async def list_servers(
    current_user: User = Depends(require_role("admin", "lawyer")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(MCPServer).order_by(MCPServer.created_at.desc()))
    return ApiResponse(data=[_server_info(s) for s in result.scalars().all()])


@router.post("/servers", status_code=status.HTTP_201_CREATED)
async def create_server(
    body: MCPServerCreate,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    server = MCPServer(
        id=uuid.uuid4(),
        name=body.name,
        transport=body.transport,
        command=body.command,
        args=body.args,
        url=body.url,
        api_key=body.api_key,
        description=body.description,
    )
    db.add(server)
    await db.commit()
    await db.refresh(server)
    await log_audit(
        user_id=str(current_user.id), action="mcp.create", resource="mcp",
        detail={"name": body.name, "transport": body.transport},
    )
    return ApiResponse(data=_server_info(server))


@router.put("/servers/{server_id}")
async def update_server(
    server_id: str,
    body: MCPServerUpdate,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(MCPServer).where(MCPServer.id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="MCP server not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(server, field, value)

    await db.commit()
    await db.refresh(server)
    await log_audit(
        user_id=str(current_user.id), action="mcp.update", resource="mcp",
        detail={"server_id": server_id, "changes": body.model_dump(exclude_unset=True)},
    )
    return ApiResponse(data=_server_info(server))


@router.delete("/servers/{server_id}")
async def delete_server(
    server_id: str,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(MCPServer).where(MCPServer.id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="MCP server not found")

    await db.delete(server)
    await db.commit()
    await log_audit(
        user_id=str(current_user.id), action="mcp.delete", resource="mcp",
        detail={"server_id": server_id, "name": server.name},
    )
    return ApiResponse(data=None)


@router.post("/servers/{server_id}/test")
async def test_connection(
    server_id: str,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(MCPServer).where(MCPServer.id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="MCP server not found")

    from contextlib import AsyncExitStack
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from mcp.client.sse import sse_client

    import json

    stack = AsyncExitStack()
    try:
        if server.transport == "sse":
            read, write = await stack.enter_async_context(sse_client(server.url))
        else:
            args_list = json.loads(server.args) if server.args else []
            params = StdioServerParameters(command=server.command or "", args=args_list)
            read, write = await stack.enter_async_context(stdio_client(params))

        session = await stack.enter_async_context(ClientSession(read, write))
        await session.initialize()
        mcp_result = await session.list_tools()
        tool_names = [t.name for t in mcp_result.tools]

        return ApiResponse(data={
            "status": "connected",
            "tools_count": len(tool_names),
            "tools": tool_names,
        })
    except Exception as e:
        return ApiResponse(data={
            "status": "error",
            "message": str(e),
        })
    finally:
        await stack.aclose()


@router.post("/servers/{server_id}/reconnect")
async def reconnect_server(
    server_id: str,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Disconnect and reconnect an MCP server, refreshing its tools."""
    result = await db.execute(select(MCPServer).where(MCPServer.id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="MCP server not found")

    from app.agent.mcp_client import get_mcp_manager
    from app.agent.registry import get_registry

    manager = get_mcp_manager()
    registry = get_registry()

    # Disconnect old
    await manager.disconnect(server_id)
    registry.unregister_mcp_tools(server_id)

    # Reconnect
    tools = await manager.connect(server)
    registry.register_mcp_tools(server_id, tools)

    return ApiResponse(data={
        "status": "connected",
        "tools_count": len(tools),
        "tools": [t.name for t in tools],
    })


@router.get("/servers/{server_id}/tools")
async def list_server_tools(
    server_id: str,
    current_user: User = Depends(require_role("admin", "lawyer")),
    db: AsyncSession = Depends(get_db),
):
    """List tools currently registered from an MCP server (without reconnecting)."""
    from app.agent.registry import get_registry

    registry = get_registry()
    prefix = f"mcp:{server_id}:"
    names = [k.split(":", 2)[-1] for k in registry._mcp if k.startswith(prefix)]

    return ApiResponse(data={
        "server_id": server_id,
        "tools_count": len(names),
        "tools": names,
    })


@router.post("/servers/{server_id}/toggle")
async def toggle_server(
    server_id: str,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Toggle an MCP server's enabled/disabled state."""
    result = await db.execute(select(MCPServer).where(MCPServer.id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="MCP server not found")

    server.enabled = not server.enabled
    await db.commit()
    await db.refresh(server)
    await log_audit(
        user_id=str(current_user.id), action="mcp.toggle", resource="mcp",
        detail={"server_id": server_id, "name": server.name, "enabled": server.enabled},
    )
    return ApiResponse(data={"id": str(server.id), "enabled": server.enabled})


def _server_info(s: MCPServer) -> MCPServerInfo:
    return MCPServerInfo(
        id=str(s.id),
        name=s.name,
        transport=s.transport,
        command=s.command,
        args=s.args,
        url=s.url,
        description=s.description,
        status=s.status,
        enabled=s.enabled,
        created_at=s.created_at.isoformat() if s.created_at else "",
        updated_at=s.updated_at.isoformat() if s.updated_at else "",
    )
