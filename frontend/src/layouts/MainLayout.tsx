import { useEffect, useState } from "react";
import { Outlet, useNavigate, useLocation } from "react-router-dom";
import { Layout, Menu, Button, Typography, Dropdown } from "antd";
import {
  MessageOutlined,
  UserOutlined,
  LogoutOutlined,
  DatabaseOutlined,
  ApiOutlined,
  ToolOutlined,
  RobotOutlined,
  SafetyCertificateOutlined,
  SettingOutlined,
  FileTextOutlined,
  TeamOutlined,
  ThunderboltOutlined,
  StarOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  BellOutlined,
  BankOutlined,
} from "@ant-design/icons";
import { useAuthStore } from "../stores/authStore";
import { getPermissionMatrix } from "../api/permissions";

const { Header, Sider, Content } = Layout;

const iconMap: Record<string, React.ReactNode> = {
  "/": <MessageOutlined />,
  "/models": <RobotOutlined />,
  "/settings": <SettingOutlined />,
  "/tools": <ToolOutlined />,
  "/mcp": <ApiOutlined />,
  "/knowledge": <DatabaseOutlined />,
  "/consultations": <FileTextOutlined />,
  "/users": <TeamOutlined />,
  "/profile": <UserOutlined />,
  "/permissions": <SafetyCertificateOutlined />,
  "/skills": <ThunderboltOutlined />,
  "/evaluations": <StarOutlined />,
};

const allMenuItems = [
  { key: "/", icon: iconMap["/"], label: "法律咨询" },
  { key: "/skills", icon: iconMap["/skills"], label: "Claude 技能" },
  { key: "/models", icon: iconMap["/models"], label: "模型配置" },
  { key: "/settings", icon: iconMap["/settings"], label: "参数设置" },
  { key: "/tools", icon: iconMap["/tools"], label: "工具管理" },
  { key: "/mcp", icon: iconMap["/mcp"], label: "MCP 服务" },
  { key: "/knowledge", icon: iconMap["/knowledge"], label: "知识库" },
  { key: "/consultations", icon: iconMap["/consultations"], label: "咨询单审核" },
  { key: "/users", icon: iconMap["/users"], label: "用户角色管理" },
  { key: "/permissions", icon: iconMap["/permissions"], label: "权限管理" },
  { key: "/evaluations", icon: iconMap["/evaluations"], label: "评估管理" },
  { key: "/profile", icon: iconMap["/profile"], label: "个人中心" },
];

const defaultRoleMenuMap: Record<string, string[]> = {
  admin: ["/", "/skills", "/models", "/settings", "/tools", "/mcp", "/knowledge", "/consultations", "/users", "/profile", "/permissions", "/evaluations"],
  lawyer: ["/", "/skills", "/models", "/settings", "/knowledge", "/consultations", "/profile", "/evaluations"],
  user: ["/", "/skills", "/consultations", "/profile"],
};

export function MainLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const logout = useAuthStore((s) => s.logout);
  const user = useAuthStore((s) => s.user);
  const [collapsed, setCollapsed] = useState(false);

  const [allowedKeys, setAllowedKeys] = useState<string[] | null>(null);

  useEffect(() => {
    getPermissionMatrix()
      .then((res) => {
        const roleData = res.data?.data?.roles;
        if (roleData && user) {
          const role = roleData.find((r) => r.role_name === user.role);
          if (role) setAllowedKeys(role.menu_keys);
        }
      })
      .catch(() => {
        const role = user?.role ?? "user";
        setAllowedKeys(defaultRoleMenuMap[role] ?? defaultRoleMenuMap.user);
      });
  }, [user]);

  const role = user?.role ?? "user";
  let visibleKeys = allowedKeys ?? defaultRoleMenuMap[role] ?? defaultRoleMenuMap.user;
  const roleDefaults = defaultRoleMenuMap[role] ?? defaultRoleMenuMap.user;
  for (const key of roleDefaults) {
    if (!visibleKeys.includes(key)) {
      visibleKeys = [...visibleKeys, key];
    }
  }
  const menuItems = allMenuItems.filter((item) => visibleKeys.includes(item.key));

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const roleLabels: Record<string, string> = {
    admin: "系统管理员",
    lawyer: "律师",
    user: "普通用户",
  };

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Sider
        width={collapsed ? 80 : 240}
        theme="dark"
        style={{
          background: "var(--sidebar-bg)",
          position: "fixed",
          left: 0,
          top: 0,
          bottom: 0,
          zIndex: 100,
          transition: "width 0.2s ease",
          overflow: "hidden",
        }}
      >
        {/* Logo & Brand */}
        <div
          style={{
            height: 64,
            display: "flex",
            alignItems: "center",
            justifyContent: collapsed ? "center" : "flex-start",
            padding: collapsed ? "0" : "0 20px",
            borderBottom: "1px solid rgba(255,255,255,0.08)",
            gap: 10,
            overflow: "hidden",
          }}
        >
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: 8,
              background: "linear-gradient(135deg, #2563eb, #1d4ed8)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
            }}
          >
            <BankOutlined style={{ color: "#fff", fontSize: 16 }} />
          </div>
          {!collapsed && (
            <Typography.Text
              strong
              style={{
                color: "#fff",
                fontSize: 16,
                whiteSpace: "nowrap",
                letterSpacing: 0.5,
              }}
            >
              AI 法律咨询
            </Typography.Text>
          )}
        </div>

        {/* Menu */}
        <div style={{ padding: "8px 0", flex: 1, overflow: "auto" }}>
          <Menu
            mode="inline"
            theme="dark"
            selectedKeys={[location.pathname]}
            items={menuItems}
            onClick={({ key }) => {
              navigate(key);
              if (window.innerWidth < 768) setCollapsed(true);
            }}
            style={{
              background: "transparent",
              borderInlineEnd: "none",
              fontSize: 14,
            }}
          />
        </div>

        {/* Collapse button */}
        <div
          style={{
            borderTop: "1px solid rgba(255,255,255,0.08)",
            padding: "12px 0",
            textAlign: "center",
          }}
        >
          <Button
            type="text"
            style={{ color: "var(--sidebar-text)" }}
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setCollapsed(!collapsed)}
          />
        </div>
      </Sider>

      <Layout style={{ marginLeft: collapsed ? 80 : 240, transition: "margin-left 0.2s ease", minHeight: "100vh" }}>
        {/* Header */}
        <Header
          style={{
            background: "rgba(255,255,255,0.95)",
            backdropFilter: "blur(8px)",
            padding: "0 24px",
            display: "flex",
            justifyContent: "flex-end",
            alignItems: "center",
            borderBottom: "1px solid var(--border)",
            height: 64,
            position: "sticky",
            top: 0,
            zIndex: 99,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <Button
              type="text"
              icon={<BellOutlined />}
              style={{ color: "var(--text-secondary)", fontSize: 16 }}
            />
            <Dropdown
              menu={{
                items: [
                  {
                    key: "profile",
                    icon: <UserOutlined />,
                    label: "个人中心",
                    onClick: () => navigate("/profile"),
                  },
                  { type: "divider" },
                  {
                    key: "logout",
                    icon: <LogoutOutlined />,
                    label: "退出登录",
                    onClick: handleLogout,
                    danger: true,
                  },
                ],
              }}
              placement="bottomRight"
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  cursor: "pointer",
                  padding: "4px 8px",
                  borderRadius: 8,
                  transition: "background 0.2s",
                }}
                onMouseEnter={(e) => (e.currentTarget.style.background = "var(--bg)")}
                onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
              >
                <div
                  style={{
                    width: 32,
                    height: 32,
                    borderRadius: "50%",
                    background: "linear-gradient(135deg, #2563eb, #7c3aed)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "#fff",
                    fontSize: 14,
                    fontWeight: 600,
                  }}
                >
                  {user?.email?.charAt(0).toUpperCase() || "U"}
                </div>
                <div style={{ textAlign: "left" }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text)", lineHeight: 1.3 }}>
                    {user?.email || "用户"}
                  </div>
                  <div style={{ fontSize: 11, color: "var(--text-secondary)", lineHeight: 1.3 }}>
                    {roleLabels[user?.role ?? ""] || user?.role || "未知"}
                  </div>
                </div>
              </div>
            </Dropdown>
          </div>
        </Header>

        {/* Content */}
        <Content
          style={{
            background: "var(--bg)",
            minHeight: "calc(100vh - 64px)",
          }}
        >
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
