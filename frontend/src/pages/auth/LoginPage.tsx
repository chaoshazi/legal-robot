import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { Form, Input, Button, Typography, message } from "antd";
import { MailOutlined, LockOutlined, BankOutlined } from "@ant-design/icons";
import { authApi } from "../../api/auth";
import { useAuthStore } from "../../stores/authStore";

export function LoginPage() {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const setAuth = useAuthStore((s) => s.setAuth);

  const onFinish = async (values: { email: string; password: string }) => {
    setLoading(true);
    try {
      const { data } = await authApi.login(values);
      if (data.data) {
        setAuth(data.data.user, data.data.access_token);
        localStorage.setItem("refresh_token", data.data.refresh_token);
        message.success("登录成功");
        navigate("/", { replace: true });
      }
    } catch {
      message.error("邮箱或密码错误");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        minHeight: "100vh",
        background: "linear-gradient(135deg, #0f172a 0%, #1e3a5f 50%, #1e40af 100%)",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Decorative background elements */}
      <div
        style={{
          position: "absolute",
          top: "-20%",
          right: "-10%",
          width: 500,
          height: 500,
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(37,99,235,0.15) 0%, transparent 70%)",
          pointerEvents: "none",
        }}
      />
      <div
        style={{
          position: "absolute",
          bottom: "-15%",
          left: "-5%",
          width: 400,
          height: 400,
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(124,58,237,0.1) 0%, transparent 70%)",
          pointerEvents: "none",
        }}
      />

      <div
        style={{
          width: 420,
          padding: "0 20px",
          position: "relative",
          zIndex: 1,
        }}
      >
        {/* Brand */}
        <div style={{ textAlign: "center", marginBottom: 40 }}>
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              width: 56,
              height: 56,
              borderRadius: 16,
              background: "linear-gradient(135deg, #2563eb, #7c3aed)",
              marginBottom: 16,
            }}
          >
            <BankOutlined style={{ color: "#fff", fontSize: 28 }} />
          </div>
          <Typography.Title level={2} style={{ color: "#fff", margin: 0, fontWeight: 700, letterSpacing: 1 }}>
            AI 法律咨询系统
          </Typography.Title>
          <Typography.Text style={{ color: "rgba(255,255,255,0.6)", fontSize: 15, marginTop: 8, display: "block" }}>
            专业 · 高效 · 智能
          </Typography.Text>
        </div>

        {/* Login Card */}
        <div
          style={{
            background: "rgba(255,255,255,0.98)",
            borderRadius: 16,
            padding: "36px 32px 28px",
            boxShadow: "0 20px 60px rgba(0,0,0,0.3)",
          }}
        >
          <Typography.Title level={4} style={{ textAlign: "center", margin: 0, marginBottom: 28, color: "#1e293b", fontWeight: 600 }}>
            欢迎回来
          </Typography.Title>

          <Form onFinish={onFinish} layout="vertical" size="large">
            <Form.Item
              name="email"
              rules={[{ required: true, message: "请输入邮箱" }]}
              style={{ marginBottom: 20 }}
            >
              <Input
                prefix={<MailOutlined style={{ color: "#94a3b8" }} />}
                placeholder="邮箱"
                style={{ borderRadius: 10, padding: "10px 14px" }}
              />
            </Form.Item>
            <Form.Item
              name="password"
              rules={[{ required: true, message: "请输入密码" }]}
              style={{ marginBottom: 28 }}
            >
              <Input.Password
                prefix={<LockOutlined style={{ color: "#94a3b8" }} />}
                placeholder="密码"
                style={{ borderRadius: 10, padding: "10px 14px" }}
              />
            </Form.Item>
            <Form.Item style={{ marginBottom: 0 }}>
              <Button
                type="primary"
                htmlType="submit"
                loading={loading}
                block
                size="large"
                style={{
                  height: 48,
                  borderRadius: 10,
                  fontSize: 16,
                  fontWeight: 600,
                  background: "linear-gradient(135deg, #2563eb, #1d4ed8)",
                  border: "none",
                  boxShadow: "0 4px 14px rgba(37,99,235,0.35)",
                }}
              >
                登录
              </Button>
            </Form.Item>
          </Form>

          <div style={{ textAlign: "center", marginTop: 24, color: "#94a3b8", fontSize: 14 }}>
            还没有账号？
            <Link
              to="/register"
              style={{ color: "#2563eb", fontWeight: 500, marginLeft: 4 }}
            >
              立即注册
            </Link>
          </div>
        </div>

        {/* Footer */}
        <div style={{ textAlign: "center", marginTop: 24, color: "rgba(255,255,255,0.35)", fontSize: 12 }}>
          AI 生成内容仅供参考，不构成法律意见
        </div>
      </div>
    </div>
  );
}
