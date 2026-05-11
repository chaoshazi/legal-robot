import client from "./client";
import type { ApiResponse, AuthTokens, CreateUserRequest, Role, User, UserAdmin } from "../types";

export const authApi = {
  register: (data: { email: string; password: string; display_name: string }) =>
    client.post<ApiResponse<AuthTokens>>("/auth/register", data),

  login: (data: { email: string; password: string }) =>
    client.post<ApiResponse<AuthTokens>>("/auth/login", data),

  refresh: (refresh_token: string) =>
    client.post<ApiResponse<{ access_token: string }>>("/auth/refresh", { refresh_token }),

  getProfile: () => client.get<ApiResponse<User>>("/users/me"),

  updateProfile: (data: Partial<User>) =>
    client.patch<ApiResponse<User>>("/users/me", data),

  changePassword: (data: { old_password: string; new_password: string }) =>
    client.post<ApiResponse<null>>("/auth/me/password", data),

  adminResetPassword: (userId: string, password: string) =>
    client.put<ApiResponse<null>>(`/users/${userId}/password`, { password }),

  // Admin: user management
  listUsers: () => client.get<ApiResponse<UserAdmin[]>>("/users"),

  createUser: (data: CreateUserRequest) =>
    client.post<ApiResponse<UserAdmin>>("/users", data),

  updateUser: (userId: string, data: { role_id?: number; is_active?: boolean }) =>
    client.put<ApiResponse<UserAdmin>>(`/users/${userId}`, data),

  deleteUser: (userId: string) =>
    client.delete<ApiResponse<null>>(`/users/${userId}`),

  // Admin: role management
  listRoles: () => client.get<ApiResponse<Role[]>>("/users/roles"),

  createRole: (data: { name: string; description?: string }) =>
    client.post<ApiResponse<Role>>("/users/roles", data),

  updateRole: (roleId: number, data: { name?: string; description?: string }) =>
    client.put<ApiResponse<Role>>(`/users/roles/${roleId}`, data),

  deleteRole: (roleId: number) =>
    client.delete<ApiResponse<null>>(`/users/roles/${roleId}`),
};
