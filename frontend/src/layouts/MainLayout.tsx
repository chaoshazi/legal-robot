import { useEffect, useState } from "react";
import { Outlet, useNavigate, useLocation } from "react-router-dom";
import { Layout, Menu, Button, Typography } from "antd";
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
  { key: "/profile", icon: iconMap["/profile"], label: "个人中心" },
];

const defaultRoleMenuMap: Record<string, string[]> = {
  admin: ["/", "/skills", "/models", "/settings", "/tools", "/mcp", "/knowledge", "/consultations", "/users", "/profile", "/permissions"],
  lawyer: ["/", "/skills", "/models", "/settings", "/knowledge", "/consultations", "/profile"],
  user: ["/", "/skills", "/consultations", "/profile"],
};

export function MainLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const logout = useAuthStore((s) => s.logout);
  const user = useAuthStore((s) => s.user);

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
        // Fallback to hardcoded defaults
        const role = user?.role ?? "user";
        setAllowedKeys(defaultRoleMenuMap[role] ?? defaultRoleMenuMap.user);
      });
  }, [user]);

  const role = user?.role ?? "user";
  let visibleKeys = allowedKeys ?? defaultRoleMenuMap[role] ?? defaultRoleMenuMap.user;
  // Merge with role defaults so new menus are visible even if backend API is stale
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

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Sider width={240} theme="light" style={{ borderRight: "1px solid #f0f0f0" }}>
        <div style={{ padding: "20px 24px", borderBottom: "1px solid #f0f0f0" }}>
          <Typography.Title level={4} style={{ margin: 0 }}>
            AI法律咨询系统
          </Typography.Title>
        </div>
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          style={{ borderInlineEnd: "none" }}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            background: "#fff",
            padding: "0 24px",
            display: "flex",
            justifyContent: "flex-end",
            alignItems: "center",
            borderBottom: "1px solid #f0f0f0",
          }}
        >
          <Button type="text" icon={<LogoutOutlined />} onClick={handleLogout}>
            退出登录
          </Button>
        </Header>
        <Content style={{ margin: 0, background: "#fff" }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
