import { useEffect, useState, useCallback } from "react";
import {
  Table, Button, Tag, Select, Switch, Space, message, Typography, Spin, Card,
  Tabs, Modal, Form, Input, Popconfirm, Tooltip,
} from "antd";
import {
  TeamOutlined, PlusOutlined, DeleteOutlined, EditOutlined, SafetyCertificateOutlined,
  UserAddOutlined, KeyOutlined,
} from "@ant-design/icons";
import { authApi } from "../../api/auth";
import type { UserAdmin, Role } from "../../types";

const roleColor: Record<string, string> = {
  admin: "red",
  lawyer: "blue",
  user: "green",
};

const roleLabel: Record<string, string> = {
  admin: "管理员",
  lawyer: "律师",
  user: "普通用户",
};

// ── 用户管理 Tab ──────────────────────────────────────────────────────────

function UserTab({
  users,
  roles,
  loading,
  onReload,
}: {
  users: UserAdmin[];
  roles: Role[];
  loading: boolean;
  onReload: () => void;
}) {
  const [createOpen, setCreateOpen] = useState(false);
  const [createForm] = Form.useForm();
  const [creating, setCreating] = useState(false);

  const [resetOpen, setResetOpen] = useState(false);
  const [resetUser, setResetUser] = useState<UserAdmin | null>(null);
  const [resetForm] = Form.useForm();
  const [resetting, setResetting] = useState(false);

  const handleCreate = async () => {
    const values = await createForm.validateFields();
    setCreating(true);
    try {
      await authApi.createUser(values);
      message.success("用户已创建");
      setCreateOpen(false);
      createForm.resetFields();
      onReload();
    } catch (e: any) {
      const detail = e?.response?.data?.detail || e?.response?.data?.message || "创建失败";
      message.error(detail);
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (userId: string) => {
    try {
      await authApi.deleteUser(userId);
      message.success("用户已删除");
      onReload();
    } catch (e: any) {
      const detail = e?.response?.data?.detail || e?.response?.data?.message || "删除失败";
      message.error(detail);
    }
  };

  const handleRoleChange = async (userId: string, roleId: number) => {
    try {
      await authApi.updateUser(userId, { role_id: roleId });
      message.success("角色已更新");
      onReload();
    } catch (e: any) {
      const detail = e?.response?.data?.detail || "更新失败";
      message.error(detail);
    }
  };

  const handleToggleActive = async (user: UserAdmin, active: boolean) => {
    try {
      await authApi.updateUser(user.id, { is_active: active });
      message.success(active ? "已启用" : "已停用");
      onReload();
    } catch (e: any) {
      const detail = e?.response?.data?.detail || "操作失败";
      message.error(detail);
    }
  };

  const openResetPassword = (user: UserAdmin) => {
    setResetUser(user);
    resetForm.resetFields();
    setResetOpen(true);
  };

  const handleResetPassword = async () => {
    if (!resetUser) return;
    const values = await resetForm.validateFields();
    setResetting(true);
    try {
      await authApi.adminResetPassword(resetUser.id, values.password);
      message.success("密码已重置");
      setResetOpen(false);
      resetForm.resetFields();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "重置失败");
    } finally {
      setResetting(false);
    }
  };

  const columns = [
    {
      title: "邮箱",
      dataIndex: "email",
      key: "email",
      width: 240,
    },
    {
      title: "昵称",
      dataIndex: "display_name",
      key: "display_name",
      width: 160,
    },
    {
      title: "角色",
      dataIndex: "role",
      key: "role",
      width: 220,
      render: (_: unknown, record: UserAdmin) => (
        <Select
          size="small"
          value={record.role_id}
          style={{ width: 160 }}
          onChange={(roleId) => handleRoleChange(record.id, roleId)}
          options={roles.map((r) => ({
            value: r.id,
            label: `${roleLabel[r.name] || r.name}（${r.name}）`,
          }))}
        />
      ),
    },
    {
      title: "状态",
      dataIndex: "is_active",
      key: "is_active",
      width: 100,
      render: (_: unknown, record: UserAdmin) => (
        <Switch
          size="small"
          checked={record.is_active}
          onChange={(checked) => handleToggleActive(record, checked)}
        />
      ),
    },
    {
      title: "注册时间",
      dataIndex: "created_at",
      key: "created_at",
      width: 170,
      render: (t: string) => t?.slice(0, 19).replace("T", " "),
    },
    {
      title: "操作",
      key: "action",
      width: 160,
      render: (_: unknown, record: UserAdmin) => (
        <Space>
          <Button size="small" icon={<KeyOutlined />} onClick={() => openResetPassword(record)}>
            重置密码
          </Button>
          <Popconfirm
            title={`确认删除用户 ${record.display_name}？`}
            description="该操作不可恢复"
            onConfirm={() => handleDelete(record.id)}
          >
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ marginBottom: 16, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <Space>
          <Typography.Text type="secondary">共 {users.length} 人</Typography.Text>
        </Space>
        <Button type="primary" icon={<UserAddOutlined />} onClick={() => setCreateOpen(true)}>
          创建用户
        </Button>
      </div>

      <Table
        dataSource={users}
        columns={columns}
        rowKey="id"
        loading={loading}
        pagination={{ pageSize: 20, showSizeChanger: false }}
        locale={{ emptyText: "暂无用户" }}
        size="middle"
      />

      <Modal
        title="创建用户"
        open={createOpen}
        onOk={handleCreate}
        onCancel={() => { setCreateOpen(false); createForm.resetFields(); }}
        confirmLoading={creating}
        width={500}
        destroyOnClose
      >
        <Form form={createForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="email" label="邮箱" rules={[{ required: true, type: "email", message: "请输入有效邮箱" }]}>
            <Input placeholder="user@example.com" />
          </Form.Item>
          <Form.Item name="display_name" label="昵称" rules={[{ required: true, message: "请输入昵称" }]}>
            <Input placeholder="用户昵称" />
          </Form.Item>
          <Form.Item name="password" label="密码" rules={[{ required: true, min: 6, message: "密码至少 6 位" }]}>
            <Input.Password placeholder="设置密码" />
          </Form.Item>
          <Form.Item name="role_id" label="角色" rules={[{ required: true, message: "请选择角色" }]}>
            <Select placeholder="选择角色" options={roles.map((r) => ({ value: r.id, label: `${roleLabel[r.name] || r.name}（${r.name}）` }))} />
          </Form.Item>
        </Form>
      </Modal>

      {/* Reset password modal */}
      <Modal
        title={`重置密码 - ${resetUser?.display_name || ""}`}
        open={resetOpen}
        onOk={handleResetPassword}
        onCancel={() => { setResetOpen(false); resetForm.resetFields(); }}
        confirmLoading={resetting}
        width={400}
        destroyOnClose
      >
        <Form form={resetForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="password" label="新密码" rules={[{ required: true, min: 6, message: "密码至少 6 位" }]}>
            <Input.Password placeholder="输入新密码" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

// ── 角色管理 Tab ──────────────────────────────────────────────────────────

function RoleTab({
  roles,
  users,
  loading,
  onReload,
}: {
  roles: Role[];
  users: UserAdmin[];
  loading: boolean;
  onReload: () => void;
}) {
  const [editOpen, setEditOpen] = useState(false);
  const [editingRole, setEditingRole] = useState<Role | null>(null);
  const [editForm] = Form.useForm();
  const [saving, setSaving] = useState(false);

  const [createOpen, setCreateOpen] = useState(false);
  const [createForm] = Form.useForm();
  const [creating, setCreating] = useState(false);

  const userCountByRole: Record<number, number> = {};
  for (const u of users) {
    userCountByRole[u.role_id] = (userCountByRole[u.role_id] || 0) + 1;
  }

  const handleCreate = async () => {
    const values = await createForm.validateFields();
    setCreating(true);
    try {
      await authApi.createRole(values);
      message.success("角色已创建");
      setCreateOpen(false);
      createForm.resetFields();
      onReload();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "创建失败");
    } finally {
      setCreating(false);
    }
  };

  const openEdit = (role: Role) => {
    setEditingRole(role);
    editForm.setFieldsValue({ name: role.name, description: role.description || "" });
    setEditOpen(true);
  };

  const handleEdit = async () => {
    if (!editingRole) return;
    const values = await editForm.validateFields();
    setSaving(true);
    try {
      await authApi.updateRole(editingRole.id, values);
      message.success("角色已更新");
      setEditOpen(false);
      onReload();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "更新失败");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (roleId: number) => {
    try {
      await authApi.deleteRole(roleId);
      message.success("角色已删除");
      onReload();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "删除失败");
    }
  };

  const columns = [
    {
      title: "角色名",
      dataIndex: "name",
      key: "name",
      width: 160,
      render: (name: string) => (
        <Space>
          <Tag color={roleColor[name] || "default"}>{roleLabel[name] || name}</Tag>
          <span>{name}</span>
        </Space>
      ),
    },
    {
      title: "描述",
      dataIndex: "description",
      key: "description",
      render: (d: string | null) => d || <Typography.Text type="secondary">-</Typography.Text>,
    },
    {
      title: "用户数",
      key: "user_count",
      width: 100,
      render: (_: unknown, record: Role) => userCountByRole[record.id] || 0,
    },
    {
      title: "操作",
      key: "action",
      width: 240,
      render: (_: unknown, record: Role) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(record)}>
            编辑
          </Button>
          <Popconfirm
            title={`确认删除角色「${roleLabel[record.name] || record.name}」？`}
            description={userCountByRole[record.id] ? "该角色下有用户，无法删除" : undefined}
            onConfirm={() => handleDelete(record.id)}
            okText="删除"
            cancelText="取消"
          >
            <Button
              size="small"
              danger
              icon={<DeleteOutlined />}
              disabled={(userCountByRole[record.id] || 0) > 0}
            >
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ marginBottom: 16, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>
          创建角色
        </Button>
      </div>

      <Table
        dataSource={roles}
        columns={columns}
        rowKey="id"
        loading={loading}
        pagination={false}
        locale={{ emptyText: "暂无角色" }}
        size="middle"
      />

      {/* Create role modal */}
      <Modal
        title="创建角色"
        open={createOpen}
        onOk={handleCreate}
        onCancel={() => { setCreateOpen(false); createForm.resetFields(); }}
        confirmLoading={creating}
        width={450}
        destroyOnClose
      >
        <Form form={createForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="name" label="角色名" rules={[{ required: true, message: "请输入角色名" }]}>
            <Input placeholder="如：editor" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} placeholder="角色描述" />
          </Form.Item>
        </Form>
      </Modal>

      {/* Edit role modal */}
      <Modal
        title="编辑角色"
        open={editOpen}
        onOk={handleEdit}
        onCancel={() => setEditOpen(false)}
        confirmLoading={saving}
        width={450}
        destroyOnClose
      >
        <Form form={editForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="name" label="角色名" rules={[{ required: true, message: "请输入角色名" }]}>
            <Input placeholder="如：editor" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} placeholder="角色描述" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

// ── 主页面 ────────────────────────────────────────────────────────────────

export function UserManagementPage() {
  const [users, setUsers] = useState<UserAdmin[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [userRes, roleRes] = await Promise.all([
        authApi.listUsers(),
        authApi.listRoles(),
      ]);
      if (userRes.data?.data) setUsers(userRes.data.data);
      if (roleRes.data?.data) setRoles(roleRes.data.data);
    } catch {
      message.error("加载数据失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div style={{ padding: 24 }}>
      <Card
        title={<span><TeamOutlined /> 用户角色管理</span>}
        extra={
          <Space>
            <Button size="small" onClick={load}>刷新</Button>
          </Space>
        }
      >
        {/* Role legend */}
        <div style={{ marginBottom: 16 }}>
          {roles.map((r) => {
            const count = users.filter((u) => u.role_id === r.id).length;
            return (
              <Tag key={r.id} color={roleColor[r.name] || "default"} style={{ marginBottom: 4 }}>
                {roleLabel[r.name] || r.name}：{r.description || "-"}（{count} 人）
              </Tag>
            );
          })}
        </div>

        <Tabs
          defaultActiveKey="users"
          items={[
            {
              key: "users",
              label: <span><TeamOutlined /> 用户管理</span>,
              children: <UserTab users={users} roles={roles} loading={loading} onReload={load} />,
            },
            {
              key: "roles",
              label: <span><KeyOutlined /> 角色管理</span>,
              children: <RoleTab roles={roles} users={users} loading={loading} onReload={load} />,
            },
          ]}
        />
      </Card>
    </div>
  );
}
