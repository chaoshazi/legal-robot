import { useEffect, useState } from "react";
import { Table, Button, Modal, Drawer, Form, Input, Select, Tag, Space, message, Popconfirm, Tooltip, Switch, List } from "antd";
import { PlusOutlined, DeleteOutlined, EditOutlined, ApiOutlined, ReloadOutlined, EyeOutlined, ToolOutlined } from "@ant-design/icons";
import type { MCPServer } from "../../types";
import { listServers, createServer, updateServer, deleteServer, testConnection, listServerTools, toggleServer } from "../../api/mcp";

const transportOptions = [
  { label: "STDIO", value: "stdio" },
  { label: "HTTP/SSE", value: "sse" },
];

const statusColor: Record<string, string> = {
  connected: "success",
  disconnected: "default",
  error: "error",
  connecting: "processing",
};

const statusLabel: Record<string, string> = {
  connected: "已连接",
  disconnected: "未连接",
  error: "错误",
  connecting: "连接中",
};

interface FormValues {
  name: string;
  transport: string;
  command: string;
  args: string;
  url: string;
  api_key: string;
  description: string;
}

const defaultValues: FormValues = {
  name: "",
  transport: "stdio",
  command: "",
  args: "",
  url: "",
  api_key: "",
  description: "",
};

export function MCPPage() {
  const [servers, setServers] = useState<MCPServer[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<MCPServer | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [testingId, setTestingId] = useState<string | null>(null);
  const [toolsDrawerOpen, setToolsDrawerOpen] = useState(false);
  const [toolsDrawerServer, setToolsDrawerServer] = useState<MCPServer | null>(null);
  const [toolsList, setToolsList] = useState<string[]>([]);
  const [toolsLoading, setToolsLoading] = useState(false);
  const [form] = Form.useForm<FormValues>();

  const load = async () => {
    setLoading(true);
    try {
      const res = await listServers();
      if (res.data) setServers(res.data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    setModalOpen(true);
  };

  const openEdit = (server: MCPServer) => {
    setEditing(server);
    form.setFieldsValue({
      name: server.name,
      transport: server.transport,
      command: server.command ?? "",
      args: server.args ?? "",
      url: server.url ?? "",
      api_key: "",
      description: server.description ?? "",
    });
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    const values = await form.validateFields();
    setSubmitting(true);
    try {
      const payload = {
        name: values.name,
        transport: values.transport,
        command: values.command || undefined,
        args: values.args || undefined,
        url: values.url || undefined,
        api_key: values.api_key || undefined,
        description: values.description || undefined,
      };

      if (editing) {
        await updateServer(editing.id, payload);
        message.success("MCP 服务器已更新");
      } else {
        await createServer(payload);
        message.success("MCP 服务器已添加");
      }
      setModalOpen(false);
      load();
    } catch {
      message.error("操作失败");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteServer(id);
      message.success("已删除");
      load();
    } catch {
      message.error("删除失败");
    }
  };

  const handleTest = async (id: string) => {
    setTestingId(id);
    try {
      const res = await testConnection(id);
      message.info(res.data?.message ?? "测试完成");
      load();
    } catch {
      message.error("连接测试失败");
    } finally {
      setTestingId(null);
    }
  };

  const handleToggle = async (server: MCPServer) => {
    try {
      const res = await toggleServer(server.id);
      message.success(res.data?.enabled ? "已启用" : "已停用");
      load();
    } catch {
      message.error("操作失败");
    }
  };

  const handleViewTools = async (server: MCPServer) => {
    setToolsDrawerServer(server);
    setToolsDrawerOpen(true);
    setToolsLoading(true);
    try {
      const res = await listServerTools(server.id);
      setToolsList(res.data?.tools ?? []);
    } catch {
      setToolsList([]);
      message.error("获取工具列表失败");
    } finally {
      setToolsLoading(false);
    }
  };

  const columns = [
    {
      title: "名称",
      dataIndex: "name",
      key: "name",
      render: (name: string, record: MCPServer) => (
        <Space>
          <ApiOutlined />
          <span>{name}</span>
          {!record.enabled && <Tag color="warning">已停用</Tag>}
        </Space>
      ),
    },
    {
      title: "传输方式",
      dataIndex: "transport",
      key: "transport",
      width: 100,
      render: (t: string) => <Tag>{t.toUpperCase()}</Tag>,
    },
    {
      title: "连接状态",
      dataIndex: "status",
      key: "status",
      width: 110,
      render: (status: string) => (
        <Tag color={statusColor[status] || "default"}>{statusLabel[status] || status}</Tag>
      ),
    },
    {
      title: "启用",
      dataIndex: "enabled",
      key: "enabled",
      width: 80,
      render: (_: unknown, record: MCPServer) => (
        <Switch size="small" checked={record.enabled} onChange={() => handleToggle(record)} />
      ),
    },
    {
      title: "描述",
      dataIndex: "description",
      key: "description",
      ellipsis: true,
      render: (d: string | null) => d ?? "-",
    },
    {
      title: "更新时间",
      dataIndex: "updated_at",
      key: "updated_at",
      width: 170,
      render: (t: string) => t?.slice(0, 19).replace("T", " "),
    },
    {
      title: "操作",
      key: "action",
      width: 200,
      render: (_: unknown, record: MCPServer) => (
        <Space>
          <Tooltip title="查看工具">
            <Button size="small" icon={<ToolOutlined />} onClick={() => handleViewTools(record)} />
          </Tooltip>
          <Tooltip title="测试连接">
            <Button
              size="small"
              icon={<ReloadOutlined />}
              loading={testingId === record.id}
              onClick={() => handleTest(record.id)}
            />
          </Tooltip>
          <Tooltip title="编辑">
            <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(record)} />
          </Tooltip>
          <Popconfirm title="确认删除该 MCP 服务器？" onConfirm={() => handleDelete(record.id)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 16, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2 style={{ margin: 0 }}>MCP 服务器管理</h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
          添加服务器
        </Button>
      </div>

      <Table
        dataSource={servers}
        columns={columns}
        rowKey="id"
        loading={loading}
        pagination={false}
      />

      <Modal
        title={editing ? "编辑 MCP 服务器" : "添加 MCP 服务器"}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        confirmLoading={submitting}
        width={600}
        destroyOnClose
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={defaultValues}
          style={{ marginTop: 16 }}
        >
          <Form.Item name="name" label="名称" rules={[{ required: true, message: "请输入名称" }]}>
            <Input placeholder="例如：My MCP Server" />
          </Form.Item>

          <Form.Item name="transport" label="传输方式" rules={[{ required: true }]}>
            <Select options={transportOptions} />
          </Form.Item>

          <Form.Item
            noStyle
            shouldUpdate={(prev, curr) => prev.transport !== curr.transport}
          >
            {({ getFieldValue }) =>
              getFieldValue("transport") === "stdio" ? (
                <>
                  <Form.Item name="command" label="命令" rules={[{ required: true, message: "请输入启动命令" }]}>
                    <Input placeholder="例如：npx" />
                  </Form.Item>
                  <Form.Item name="args" label="参数">
                    <Input.TextArea rows={2} placeholder='例如：["@modelcontextprotocol/server-filesystem", "/path"]' />
                  </Form.Item>
                </>
              ) : (
                <>
                  <Form.Item name="url" label="服务 URL" rules={[{ required: true, message: "请输入 URL" }]}>
                    <Input placeholder="例如：http://localhost:3000/sse" />
                  </Form.Item>
                  <Form.Item name="api_key" label="API Key">
                    <Input.Password placeholder="可选" />
                  </Form.Item>
                </>
              )
            }
          </Form.Item>

          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} placeholder="可选描述" />
          </Form.Item>
        </Form>
      </Modal>

      <Drawer
        title={`${toolsDrawerServer?.name ?? ""} — 可用工具`}
        placement="right"
        width={400}
        open={toolsDrawerOpen}
        onClose={() => setToolsDrawerOpen(false)}
      >
        <List
          loading={toolsLoading}
          dataSource={toolsList}
          locale={{ emptyText: "该服务器暂无注册工具" }}
          renderItem={(tool) => (
            <List.Item>
              <Space>
                <ToolOutlined />
                <span>{tool}</span>
              </Space>
            </List.Item>
          )}
        />
      </Drawer>
    </div>
  );
}
