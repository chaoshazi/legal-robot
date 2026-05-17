import uuid
from datetime import datetime, timedelta, timezone
from hashlib import sha256

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.token import RefreshToken
from app.models.user import Role, User
from app.schemas.auth import (
    AuthResponse,
    ChangePasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UpdateUserRequest,
    UserInfo,
)
from app.schemas.common import ApiResponse
from app.services.audit import log_audit

router = APIRouter()


@router.post("/register")
@limiter.limit("5/minute")
async def register(req: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == req.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    role_result = await db.execute(select(Role).where(Role.name == "user"))
    user_role = role_result.scalar_one()

    user = User(
        id=uuid.uuid4(),
        email=req.email,
        display_name=req.display_name,
        hashed_password=hash_password(req.password),
        role_id=user_role.id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    access = create_access_token(str(user.id), user.role.name)
    refresh = create_refresh_token(str(user.id))
    await _save_refresh(db, user.id, refresh)

    return ApiResponse(data=AuthResponse(access_token=access, refresh_token=refresh, user=_to_info(user)))


@router.post("/login")
@limiter.limit("10/minute")
async def login(req: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).options(selectinload(User.role)).where(User.email == req.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

    access = create_access_token(str(user.id), user.role.name)
    refresh = create_refresh_token(str(user.id))
    await _save_refresh(db, user.id, refresh)

    await log_audit(user_id=str(user.id), action="login", resource="auth", detail={"email": user.email})
    return ApiResponse(data=AuthResponse(access_token=access, refresh_token=refresh, user=_to_info(user)))


@router.post("/refresh")
async def refresh(req: RefreshRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_token(req.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    token_hash = sha256(req.refresh_token.encode()).hexdigest()
    stored = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked == False,  # noqa: E712
        )
    )
    stored_token = stored.scalar_one_or_none()
    if not stored_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked")
    if stored_token.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired")

    stored_token.revoked = True
    user_id = payload["sub"]
    new_access = create_access_token(user_id, payload.get("role", "user"))
    new_refresh = create_refresh_token(user_id)
    await _save_refresh(db, str(user_id), new_refresh)
    await db.commit()

    return ApiResponse(data=TokenResponse(access_token=new_access))


@router.post("/me/password")
async def change_password(
    req: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(req.old_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="旧密码错误")
    if len(req.new_password) < 6:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="新密码至少 6 位")

    current_user.hashed_password = hash_password(req.new_password)
    await db.commit()
    return ApiResponse(message="密码已修改")


async def _save_refresh(db: AsyncSession, user_id: uuid.UUID | str, token: str):
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    db.add(RefreshToken(
        user_id=user_id,
        token_hash=sha256(token.encode()).hexdigest(),
        expires_at=expires_at,
    ))
    await db.commit()


def _to_info(user: User) -> UserInfo:
    return UserInfo(
        id=str(user.id),
        email=user.email,
        display_name=user.display_name,
        role=user.role.name,
        is_active=user.is_active,
        created_at=user.created_at.isoformat() if user.created_at else "",
    )
