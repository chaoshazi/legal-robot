import { useEffect, useState } from "react";
import { Table, Button, Modal, Form, Input, Select, Tag, Space, message, Popconfirm, Switch } from "antd";
import { PlusOutlined, DeleteOutlined, EditOutlined, ToolOutlined } from "@ant-design/icons";
import type { Tool } from "../../types";
import { listTools, createTool, updateTool, deleteTool } from "../../api/tools";

interface FormValues {
  name: string;
  description: string;
  function_name: string;
  parameters: string;
  tool_type: string;
}

const defaultValues: FormValues = {
  name: "",
  description: "",
  function_name: "",
  parameters: "",
  tool_type: "custom",
};

export function ToolsPage() {
  const [tools, setTools] = useState<Tool[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Tool | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [form] = Form.useForm<FormValues>();

  const load = async () => {
    setLoading(true);
    try {
      const res = await listTools();
      if (res.data) setTools(res.data);
    } catch (e) {
      console.warn("Failed to load tools", e);
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

  const openEdit = (tool: Tool) => {
    setEditing(tool);
    form.setFieldsValue({
      name: tool.name,
      description: tool.description,
      function_name: tool.function_name,
      parameters: tool.parameters ?? "",
      tool_type: tool.tool_type,
    });
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    const values = await form.validateFields();
    setSubmitting(true);
    try {
      const payload = {
        ...values,
        parameters: values.parameters || undefined,
      };

      if (editing) {
        await updateTool(editing.id, payload);
        message.success("工具已更新");
      } else {
        await createTool(payload);
        message.success("工具已添加");
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
      await deleteTool(id);
      message.success("已删除");
      load();
    } catch {
      message.error("删除失败");
    }
  };

  const handleToggleEnabled = async (tool: Tool, enabled: boolean) => {
    try {
      await updateTool(tool.id, { enabled });
      message.success(enabled ? "已启用" : "已停用");
      load();
    } catch {
      message.error("操作失败");
    }
  };

  const columns = [
    {
      title: "名称",
      dataIndex: "name",
      key: "name",
      render: (name: string, record: Tool) => (
        <Space>
          <ToolOutlined />
          <span>{name}</span>
          {record.tool_type === "builtin" && <Tag color="blue">内置</Tag>}
          {!record.enabled && <Tag color="warning">已停用</Tag>}
        </Space>
      ),
    },
    {
      title: "函数名",
      dataIndex: "function_name",
      key: "function_name",
      width: 160,
    },
    {
      title: "描述",
      dataIndex: "description",
      key: "description",
      ellipsis: true,
    },
    {
      title: "启用",
      dataIndex: "enabled",
      key: "enabled",
      width: 80,
      render: (_: unknown, record: Tool) => (
        <Switch
          size="small"
          checked={record.enabled}
          onChange={(checked) => handleToggleEnabled(record, checked)}
        />
      ),
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
      width: 160,
      render: (_: unknown, record: Tool) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(record)}>
            编辑
          </Button>
          {record.tool_type !== "builtin" && (
            <Popconfirm title="确认删除该工具？" onConfirm={() => handleDelete(record.id)}>
              <Button size="small" danger icon={<DeleteOutlined />} />
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 16, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2 style={{ margin: 0 }}>工具管理</h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
          添加工具
        </Button>
      </div>

      <Table
        dataSource={tools}
        columns={columns}
        rowKey="id"
        loading={loading}
        pagination={false}
      />

      <Modal
        title={editing ? "编辑工具" : "添加工具"}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        confirmLoading={submitting}
        width={600}
        destroyOnClose
      >
        <Form form={form} layout="vertical" initialValues={defaultValues} style={{ marginTop: 16 }}>
          <Form.Item name="name" label="名称" rules={[{ required: true, message: "请输入名称" }]}>
            <Input placeholder="例如：法律检索" />
          </Form.Item>

          <Form.Item
            name="function_name"
            label="函数名"
            rules={[{ required: true, message: "请输入函数名" }]}
          >
            <Input placeholder="例如：search_laws" disabled={editing?.tool_type === "builtin"} />
          </Form.Item>

          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} placeholder="工具功能描述" />
          </Form.Item>

          <Form.Item name="parameters" label="参数定义 (JSON Schema)">
            <Input.TextArea
              rows={3}
              placeholder='{"type":"object","properties":{"query":{"type":"string"}}}'
            />
          </Form.Item>

          <Form.Item name="tool_type" label="类型" hidden>
            <Input />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
