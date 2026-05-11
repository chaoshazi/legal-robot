import client from "./client";
import type { ApiResponse, PermissionMatrix } from "../types";

export function getPermissionMatrix() {
  return client.get<ApiResponse<{ roles: PermissionMatrix["roles"]; menus: PermissionMatrix["menus"] }>>("/permissions/roles");
}

export function updateRoleMenus(roleId: number, menuKeys: string[]) {
  return client.put(`/permissions/roles/${roleId}`, { menu_keys: menuKeys });
}
