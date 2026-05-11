import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { Form, Input, Button, Card, Typography, message } from "antd";
import { MailOutlined, LockOutlined, UserOutlined } from "@ant-design/icons";
import { authApi } from "../../api/auth";
import { useAuthStore } from "../../stores/authStore";

export function RegisterPage() {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const setAuth = useAuthStore((s) => s.setAuth);

  const onFinish = async (values: { email: string; password: string; display_name: string }) => {
    setLoading(true);
    try {
      const { data } = await authApi.register(values);
      if (data.data) {
        setAuth(data.data.user, data.data.access_token);
        localStorage.setItem("refresh_token", data.data.refresh_token);
        message.success("注册成功");
        navigate("/", { replace: true });
      }
    } catch {
      message.error("注册失败，请重试");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "100vh", background: "#f5f5f5" }}>
      <Card style={{ width: 400 }}>
        <Typography.Title level={3} style={{ textAlign: "center", marginBottom: 32 }}>
          注册
        </Typography.Title>
        <Form onFinish={onFinish} layout="vertical" size="large">
          <Form.Item name="display_name" rules={[{ required: true, message: "请输入昵称" }]}>
            <Input prefix={<UserOutlined />} placeholder="昵称" />
          </Form.Item>
          <Form.Item name="email" rules={[{ required: true, type: "email", message: "请输入有效邮箱" }]}>
            <Input prefix={<MailOutlined />} placeholder="邮箱" />
          </Form.Item>
          <Form.Item name="password" rules={[{ required: true, min: 6, message: "密码至少 6 位" }]}>
            <Input.Password prefix={<LockOutlined />} placeholder="密码" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block>
              注册
            </Button>
          </Form.Item>
        </Form>
        <div style={{ textAlign: "center" }}>
          已有账号？<Link to="/login">立即登录</Link>
        </div>
      </Card>
    </div>
  );
}
