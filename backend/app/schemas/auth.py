from pydantic import BaseModel


class UserInfo(BaseModel):
    id: str
    email: str
    display_name: str
    role: str
    is_active: bool
    created_at: str


class RegisterRequest(BaseModel):
    email: str
    password: str
    display_name: str


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: UserInfo


class TokenResponse(BaseModel):
    access_token: str


class UpdateUserRequest(BaseModel):
    display_name: str | None = None
    phone: str | None = None


class UserAdminInfo(BaseModel):
    id: str
    email: str
    display_name: str
    phone: str | None = None
    role_id: int
    role: str
    is_active: bool
    created_at: str


class UpdateUserAdminRequest(BaseModel):
    role_id: int | None = None
    is_active: bool | None = None


class RoleInfo(BaseModel):
    id: int
    name: str
    description: str | None = None


class CreateUserAdminRequest(BaseModel):
    email: str
    password: str
    display_name: str
    role_id: int


class CreateRoleRequest(BaseModel):
    name: str
    description: str | None = None


class UpdateRoleRequest(BaseModel):
    name: str | None = None
    description: str | None = None


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class AdminResetPasswordRequest(BaseModel):
    password: str
