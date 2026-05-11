from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.core.database import get_db
from app.models.role_menu import RoleMenu
from app.models.user import Role, User
from app.schemas.common import ApiResponse
from pydantic import BaseModel

router = APIRouter()

ALL_MENUS = [
    {"key": "/", "label": "法律咨询"},
    {"key": "/models", "label": "模型配置"},
    {"key": "/settings", "label": "参数设置"},
    {"key": "/tools", "label": "工具管理"},
    {"key": "/mcp", "label": "MCP 服务"},
    {"key": "/knowledge", "label": "知识库"},
    {"key": "/consultations", "label": "咨询单审核"},
    {"key": "/users", "label": "用户管理"},
    {"key": "/profile", "label": "个人中心"},
    {"key": "/permissions", "label": "权限管理"},
]


class RolePermissionOut(BaseModel):
    role_id: int
    role_name: str
    menu_keys: list[str]


class UpdateRoleMenusIn(BaseModel):
    menu_keys: list[str]


@router.get("/roles")
async def list_role_permissions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all roles with their allowed menu keys."""
    result = await db.execute(select(Role).order_by(Role.id))
    roles = result.scalars().all()

    perm_result = await db.execute(
        select(RoleMenu).where(RoleMenu.enabled.is_(True))
    )
    enabled_map: dict[int, list[str]] = {}
    for rm in perm_result.scalars().all():
        enabled_map.setdefault(rm.role_id, []).append(rm.menu_key)

    out: list[RolePermissionOut] = []
    for r in roles:
        keys = enabled_map.get(r.id, [])
        if not keys:
            keys = [m["key"] for m in ALL_MENUS]
        out.append(RolePermissionOut(role_id=r.id, role_name=r.name, menu_keys=keys))

    return ApiResponse(data={"roles": out, "menus": ALL_MENUS})


@router.put("/roles/{role_id}")
async def update_role_menus(
    role_id: int,
    body: UpdateRoleMenusIn,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Replace a role's allowed menu keys."""
    result = await db.execute(select(Role).where(Role.id == role_id))
    if not result.scalar_one_or_none():
        return ApiResponse(code=2001, message="Role not found")

    # Delete existing + insert new in one transaction
    old = await db.execute(
        select(RoleMenu).where(RoleMenu.role_id == role_id)
    )
    for rm in old.scalars().all():
        await db.delete(rm)

    for key in body.menu_keys:
        db.add(RoleMenu(role_id=role_id, menu_key=key, enabled=True))

    await db.commit()
    return ApiResponse(data={"role_id": role_id, "menu_keys": body.menu_keys})
