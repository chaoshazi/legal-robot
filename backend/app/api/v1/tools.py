import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.core.database import get_db
from app.models.tool import Tool
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.tool import CreateToolRequest, ToolInfo, UpdateToolRequest

router = APIRouter()


def _tool_info(t: Tool) -> ToolInfo:
    return ToolInfo(
        id=str(t.id),
        name=t.name,
        description=t.description or "",
        function_name=t.function_name,
        parameters=t.parameters,
        tool_type=t.tool_type,
        enabled=t.enabled,
        created_at=t.created_at.isoformat() if t.created_at else "",
        updated_at=t.updated_at.isoformat() if t.updated_at else "",
    )


@router.get("")
async def list_tools(
    current_user: User = Depends(require_role("admin", "lawyer")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Tool).order_by(Tool.created_at))
    db_tools = result.scalars().all()

    # Merge with registry builtin tools so the frontend always sees them
    from app.agent.registry import get_registry
    registry = get_registry()
    db_func_names = {t.function_name for t in db_tools}

    all_tools = [_tool_info(t) for t in db_tools]
    for func_name, tool in registry._builtin.items():
        if func_name not in db_func_names:
            all_tools.append(ToolInfo(
                id=f"builtin:{func_name}",
                name=func_name,
                description=tool.description or "",
                function_name=func_name,
                parameters=None,
                tool_type="builtin",
                enabled=True,
                created_at="",
                updated_at="",
            ))

    return ApiResponse(data=all_tools)


@router.post("")
async def create_tool(
    body: CreateToolRequest,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    tool = Tool(
        id=uuid.uuid4(),
        name=body.name,
        description=body.description,
        function_name=body.function_name,
        parameters=body.parameters,
        tool_type=body.tool_type,
        enabled=body.enabled,
    )
    db.add(tool)
    await db.commit()
    await db.refresh(tool)
    return ApiResponse(data=_tool_info(tool))


@router.put("/{tool_id}")
async def update_tool(
    tool_id: str,
    body: UpdateToolRequest,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Tool).where(Tool.id == tool_id))
    tool = result.scalar_one_or_none()
    if not tool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found")

    patch = body.model_dump(exclude_none=True)
    for key, value in patch.items():
        setattr(tool, key, value)
    await db.commit()
    await db.refresh(tool)
    return ApiResponse(data=_tool_info(tool))


@router.delete("/{tool_id}")
async def delete_tool(
    tool_id: str,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Tool).where(Tool.id == tool_id))
    tool = result.scalar_one_or_none()
    if not tool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found")
    await db.delete(tool)
    await db.commit()
    return ApiResponse(data=None)
