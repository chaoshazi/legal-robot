import { useEffect, useState } from "react";
import { Card, Form, Input, Button, Descriptions, message, Typography, Divider } from "antd";
import { authApi } from "../../api/auth";
import type { User } from "../../types";

export function ProfilePage() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(false);
  const [pwdLoading, setPwdLoading] = useState(false);
  const [pwdForm] = Form.useForm();

  const loadUser = async () => {
    try {
      const { data } = await authApi.getProfile();
      if (data.data) setUser(data.data);
    } catch {
      message.error("获取用户信息失败");
    }
  };

  useEffect(() => {
    loadUser();
  }, []);

  const onFinish = async (values: { display_name: string }) => {
    setLoading(true);
    try {
      const { data } = await authApi.updateProfile(values);
      if (data.data) {
        setUser(data.data);
        message.success("更新成功");
      }
    } catch {
      message.error("更新失败");
    } finally {
      setLoading(false);
    }
  };

  const onChangePassword = async (values: { old_password: string; new_password: string; confirm: string }) => {
    if (values.new_password !== values.confirm) {
      message.error("两次输入的新密码不一致");
      return;
    }
    setPwdLoading(true);
    try {
      await authApi.changePassword({ old_password: values.old_password, new_password: values.new_password });
      message.success("密码已修改");
      pwdForm.resetFields();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "修改密码失败");
    } finally {
      setPwdLoading(false);
    }
  };

  if (!user) return null;

  return (
    <div style={{ maxWidth: 600, margin: "24px auto" }}>
      <Card title="个人信息">
        <Descriptions column={1} style={{ marginBottom: 24 }}>
          <Descriptions.Item label="邮箱">{user.email}</Descriptions.Item>
          <Descriptions.Item label="角色">{user.role}</Descriptions.Item>
          <Descriptions.Item label="注册时间">{user.created_at}</Descriptions.Item>
        </Descriptions>
        <Typography.Title level={5}>修改昵称</Typography.Title>
        <Form onFinish={onFinish} layout="inline" initialValues={{ display_name: user.display_name }}>
          <Form.Item name="display_name" rules={[{ required: true, message: "请输入昵称" }]}>
            <Input />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading}>
              保存
            </Button>
          </Form.Item>
        </Form>

        <Divider />

        <Typography.Title level={5}>修改密码</Typography.Title>
        <Form form={pwdForm} onFinish={onChangePassword} layout="vertical" style={{ maxWidth: 360 }}>
          <Form.Item name="old_password" label="当前密码" rules={[{ required: true, message: "请输入当前密码" }]}>
            <Input.Password placeholder="输入当前密码" />
          </Form.Item>
          <Form.Item name="new_password" label="新密码" rules={[{ required: true, min: 6, message: "新密码至少 6 位" }]}>
            <Input.Password placeholder="输入新密码" />
          </Form.Item>
          <Form.Item name="confirm" label="确认新密码" rules={[{ required: true, message: "请再次输入新密码" }]}>
            <Input.Password placeholder="再次输入新密码" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={pwdLoading}>
              修改密码
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}
