import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, require_role
from app.core.database import get_db
from app.core.security import hash_password
from app.models.token import RefreshToken
from app.models.user import Role, User
from app.schemas.auth import (
    AdminResetPasswordRequest,
    CreateRoleRequest,
    CreateUserAdminRequest,
    RoleInfo,
    UpdateRoleRequest,
    UpdateUserAdminRequest,
    UpdateUserRequest,
    UserAdminInfo,
    UserInfo,
)
from app.schemas.common import ApiResponse
from app.services.audit import log_audit

router = APIRouter()


# ── Own profile ────────────────────────────────────────────────────────────


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return ApiResponse(data=_to_info(current_user))


@router.patch("/me")
async def update_me(
    req: UpdateUserRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if req.display_name is not None:
        current_user.display_name = req.display_name
    if req.phone is not None:
        current_user.phone = req.phone
    await db.commit()
    await db.refresh(current_user)
    return ApiResponse(data=_to_info(current_user))


# ── Admin: User management ────────────────────────────────────────────────


@router.get("")
async def list_users(
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """List all users (admin only)."""
    result = await db.execute(
        select(User).options(selectinload(User.role)).order_by(User.created_at.desc())
    )
    return ApiResponse(data=[_admin_info(u) for u in result.scalars().all()])


@router.put("/{user_id}")
async def update_user(
    user_id: str,
    req: UpdateUserAdminRequest,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Update user role or status (admin only)."""
    result = await db.execute(
        select(User).options(selectinload(User.role)).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if req.role_id is not None:
        role_result = await db.execute(select(Role).where(Role.id == req.role_id))
        role = role_result.scalar_one_or_none()
        if not role:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Role not found")
        user.role_id = req.role_id
    if req.is_active is not None:
        user.is_active = req.is_active

    await db.commit()
    await db.refresh(user)
    await log_audit(
        user_id=str(current_user.id), action="user.update", resource="users",
        detail={"target_user_id": user_id, "changes": req.model_dump(exclude_none=True)},
    )
    return ApiResponse(data=_admin_info(user))


# ── Admin: Create / delete user ────────────────────────────────────────────


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_user(
    req: CreateUserAdminRequest,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new user (admin only)."""
    existing = await db.execute(select(User).where(User.email == req.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        id=uuid.uuid4(),
        email=req.email,
        display_name=req.display_name,
        hashed_password=hash_password(req.password),
        role_id=req.role_id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    # Reload with role relationship
    result = await db.execute(
        select(User).options(selectinload(User.role)).where(User.id == user.id)
    )
    await log_audit(
        user_id=str(current_user.id), action="user.create", resource="users",
        detail={"email": req.email, "display_name": req.display_name, "role_id": str(req.role_id)},
    )
    return ApiResponse(data=_admin_info(result.scalar_one()))


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Delete a user (admin only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if str(user.id) == str(current_user.id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete yourself")
    await db.execute(delete(RefreshToken).where(RefreshToken.user_id == user.id))
    await db.delete(user)
    await db.commit()
    await log_audit(
        user_id=str(current_user.id), action="user.delete", resource="users",
        detail={"target_user_id": user_id, "email": user.email},
    )
    return ApiResponse(data=None)


@router.put("/{user_id}/password")
async def admin_reset_password(
    user_id: str,
    req: AdminResetPasswordRequest,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Admin reset any user's password."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if len(req.password) < 6:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="密码至少 6 位")
    user.hashed_password = hash_password(req.password)
    await db.commit()
    await log_audit(
        user_id=str(current_user.id), action="user.reset_password", resource="users",
        detail={"target_user_id": user_id},
    )
    return ApiResponse(message="密码已重置")


# ── Role CRUD ──────────────────────────────────────────────────────────────


@router.get("/roles")
async def list_roles(
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """List all roles (admin only)."""
    result = await db.execute(select(Role).order_by(Role.id))
    return ApiResponse(data=[_role_info(r) for r in result.scalars().all()])


@router.post("/roles", status_code=status.HTTP_201_CREATED)
async def create_role(
    req: CreateRoleRequest,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new role (admin only)."""
    existing = await db.execute(select(Role).where(Role.name == req.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Role name already exists")
    role = Role(name=req.name, description=req.description)
    db.add(role)
    await db.commit()
    await db.refresh(role)
    await log_audit(
        user_id=str(current_user.id), action="role.create", resource="users",
        detail={"name": req.name},
    )
    return ApiResponse(data=_role_info(role))


@router.put("/roles/{role_id}")
async def update_role(
    role_id: int,
    req: UpdateRoleRequest,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Update a role (admin only)."""
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    if req.name is not None:
        role.name = req.name
    if req.description is not None:
        role.description = req.description
    await db.commit()
    await db.refresh(role)
    await log_audit(
        user_id=str(current_user.id), action="role.update", resource="users",
        detail={"role_id": role_id, "changes": req.model_dump(exclude_none=True)},
    )
    return ApiResponse(data=_role_info(role))


@router.delete("/roles/{role_id}")
async def delete_role(
    role_id: int,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Delete a role (admin only). Cannot delete roles that have users."""
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    user_count = await db.execute(select(User).where(User.role_id == role_id))
    if user_count.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete role that has users assigned",
        )

    await db.delete(role)
    await db.commit()
    await log_audit(
        user_id=str(current_user.id), action="role.delete", resource="users",
        detail={"role_id": role_id, "name": role.name},
    )
    return ApiResponse(data=None)


# ── Helpers ────────────────────────────────────────────────────────────────


def _to_info(user: User) -> UserInfo:
    return UserInfo(
        id=str(user.id),
        email=user.email,
        display_name=user.display_name,
        role=user.role.name,
        is_active=user.is_active,
        created_at=user.created_at.isoformat() if user.created_at else "",
    )


def _admin_info(user: User) -> UserAdminInfo:
    return UserAdminInfo(
        id=str(user.id),
        email=user.email,
        display_name=user.display_name,
        phone=user.phone,
        role_id=user.role_id,
        role=user.role.name,
        is_active=user.is_active,
        created_at=user.created_at.isoformat() if user.created_at else "",
    )


def _role_info(role: Role) -> RoleInfo:
    return RoleInfo(
        id=role.id,
        name=role.name,
        description=role.description,
    )
