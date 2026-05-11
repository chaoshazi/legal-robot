import { Navigate } from "react-router-dom";
import type { RouteObject } from "react-router-dom";
import { MainLayout } from "../layouts/MainLayout";
import { LoginPage } from "../pages/auth/LoginPage";
import { RegisterPage } from "../pages/auth/RegisterPage";
import { ChatPage } from "../pages/chat/ChatPage";
import { ProfilePage } from "../pages/profile/ProfilePage";
import { KnowledgePage } from "../pages/knowledge/KnowledgePage";
import { MCPPage } from "../pages/mcp/MCPPage";
import { ToolsPage } from "../pages/tools/ToolsPage";
import { PermissionsPage } from "../pages/permissions/PermissionsPage";
import { ModelConfigPage } from "../pages/models/ModelConfigPage";
import { ParameterSettingsPage } from "../pages/settings/ParameterSettingsPage";
import { ConsultationReviewPage } from "../pages/consultation/ConsultationReviewPage";
import { UserManagementPage } from "../pages/users/UserManagementPage";
import { SkillsPage } from "../pages/skills/SkillsPage";
import { useAuthStore } from "../stores/authStore";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem("access_token");
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

function RoleGuard({ roles, children }: { roles: string[]; children: React.ReactNode }) {
  const user = useAuthStore((s) => s.user);
  const isRestoring = useAuthStore((s) => s.isRestoring);

  if (isRestoring) return null;
  if (!user || !roles.includes(user.role)) {
    return <Navigate to="/" replace />;
  }
  return <>{children}</>;
}

export const routerConfig: RouteObject[] = [
  {
    path: "/login",
    element: <LoginPage />,
  },
  {
    path: "/register",
    element: <RegisterPage />,
  },
  {
    path: "/",
    element: (
      <ProtectedRoute>
        <MainLayout />
      </ProtectedRoute>
    ),
    children: [
      { index: true, element: <ChatPage /> },
      { path: "profile", element: <ProfilePage /> },
      {
        path: "consultations",
        element: (
          <RoleGuard roles={["admin", "lawyer", "user"]}>
            <ConsultationReviewPage />
          </RoleGuard>
        ),
      },
      {
        path: "knowledge",
        element: (
          <RoleGuard roles={["admin", "lawyer"]}>
            <KnowledgePage />
          </RoleGuard>
        ),
      },
      {
        path: "mcp",
        element: (
          <RoleGuard roles={["admin"]}>
            <MCPPage />
          </RoleGuard>
        ),
      },
      {
        path: "tools",
        element: (
          <RoleGuard roles={["admin"]}>
            <ToolsPage />
          </RoleGuard>
        ),
      },
      {
        path: "models",
        element: (
          <RoleGuard roles={["admin", "lawyer"]}>
            <ModelConfigPage />
          </RoleGuard>
        ),
      },
      {
        path: "settings",
        element: (
          <RoleGuard roles={["admin", "lawyer"]}>
            <ParameterSettingsPage />
          </RoleGuard>
        ),
      },
      {
        path: "permissions",
        element: (
          <RoleGuard roles={["admin"]}>
            <PermissionsPage />
          </RoleGuard>
        ),
      },
      {
        path: "users",
        element: (
          <RoleGuard roles={["admin"]}>
            <UserManagementPage />
          </RoleGuard>
        ),
      },
      {
        path: "skills",
        element: (
          <RoleGuard roles={["admin", "lawyer", "user"]}>
            <SkillsPage />
          </RoleGuard>
        ),
      },
    ],
  },
  {
    path: "*",
    element: <Navigate to="/" replace />,
  },
];
