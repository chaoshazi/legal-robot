import { useEffect, useState } from "react";
import { Table, Button, Upload, Tag, message, Space, Popconfirm, Switch, Steps, Typography, Spin, Divider } from "antd";
import { UploadOutlined, DeleteOutlined, PlayCircleOutlined } from "@ant-design/icons";
import client from "../../api/client";
import { getUnifiedConfig, updateUnifiedConfig } from "../../api/settings";

interface Document {
  id: string;
  filename: string;
  file_size: number;
  chunk_count: number | null;
  status: string;
  error: string | null;
  created_at: string;
}

export function KnowledgePage() {
  const [docs, setDocs] = useState<Document[]>([]);
  const [loading, setLoading] = useState(false);
  const [ingesting, setIngesting] = useState<string | null>(null);
  const [enabledIds, setEnabledIds] = useState<string[]>([]);
  const [configLoading, setConfigLoading] = useState(false);

  const loadDocs = async () => {
    setLoading(true);
    try {
      const { data } = await client.get("/knowledge/documents");
      if (data.data) setDocs(data.data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  const loadConfig = async () => {
    setConfigLoading(true);
    try {
      const res = await getUnifiedConfig();
      if (res.data?.active_knowledge_ids) {
        setEnabledIds(res.data.active_knowledge_ids);
      }
    } catch {
      // ignore
    } finally {
      setConfigLoading(false);
    }
  };

  useEffect(() => {
    loadDocs();
    loadConfig();
  }, []);

  const toggleEnabled = async (docId: string, checked: boolean) => {
    const next = checked
      ? [...enabledIds, docId]
      : enabledIds.filter((id) => id !== docId);

    // Optimistic update
    setEnabledIds(next);

    try {
      const res = await getUnifiedConfig();
      if (!res.data) throw new Error("no config");
      await updateUnifiedConfig({ ...res.data, active_knowledge_ids: next });
    } catch {
      message.error("保存失败");
      loadConfig(); // revert
    }
  };

  const handleUpload = async (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    try {
      await client.post("/knowledge/upload", formData, {
        headers: { "Content-Type": null },
      });
      message.success(`${file.name} 上传成功`);
      loadDocs();
    } catch (e: any) {
      const detail = e?.response?.data?.detail || e?.response?.data?.message || e.message || "未知错误";
      message.error(`上传失败: ${detail}`);
    }
    return false;
  };

  const handleIngest = async (docId: string) => {
    setIngesting(docId);
    const hideLoading = message.loading("正在入库，PDF 可能需要 30-60 秒...", 0);
    try {
      const { data } = await client.post(`/knowledge/ingest/${docId}`);
      hideLoading();
      if (data.data) {
        message.success("入库完成");
        loadDocs();
      }
    } catch (e: any) {
      hideLoading();
      const resp = e?.response?.data;
      const detail = resp?.detail || e?.message || "";
      if (detail.includes("Already ingested")) {
        message.info("该文档已入库，无需重复操作");
        loadDocs();
      } else if (e.code === "ECONNABORTED" || detail.includes("timeout")) {
        message.warning("处理超时，但后台可能仍在处理，请稍后刷新查看状态");
        loadDocs();
      } else {
        message.error("入库失败: " + (detail || "未知错误"));
      }
    } finally {
      setIngesting(null);
    }
  };

  const handleDelete = async (docId: string) => {
    try {
      await client.delete(`/knowledge/documents/${docId}`);
      // Also remove from enabled list if present
      setEnabledIds((prev) => prev.filter((id) => id !== docId));
      message.success("已删除");
      loadDocs();
    } catch {
      message.error("删除失败");
    }
  };

  const statusColor: Record<string, string> = {
    uploaded: "default",
    ingesting: "processing",
    ingested: "success",
    failed: "error",
  };

  const statusLabel: Record<string, string> = {
    uploaded: "待入库",
    ingesting: "入库中",
    ingested: "已入库",
    failed: "失败",
  };

  const columns = [
    {
      title: "文件名",
      dataIndex: "filename",
      key: "filename",
    },
    {
      title: "大小",
      dataIndex: "file_size",
      key: "file_size",
      render: (size: number) => `${(size / 1024).toFixed(1)} KB`,
    },
    {
      title: "分块数",
      dataIndex: "chunk_count",
      key: "chunk_count",
      render: (v: number | null) => v ?? "-",
    },
    {
      title: "入库状态",
      dataIndex: "status",
      key: "status",
      render: (status: string) => (
        <Tag color={statusColor[status] || "default"}>{statusLabel[status] || status}</Tag>
      ),
    },
    {
      title: "错误",
      dataIndex: "error",
      key: "error",
      render: (err: string | null) => err && <span style={{ color: "red" }}>{err}</span>,
    },
    {
      title: "已启用",
      key: "enabled",
      render: (_: any, record: Document) => {
        const isIngested = record.status === "ingested";
        return (
          <Switch
            checked={enabledIds.includes(record.id)}
            disabled={!isIngested || configLoading}
            onChange={(checked) => toggleEnabled(record.id, checked)}
            size="small"
          />
        );
      },
    },
    {
      title: "上传时间",
      dataIndex: "created_at",
      key: "created_at",
      render: (t: string) => t?.slice(0, 19).replace("T", " "),
    },
    {
      title: "操作",
      key: "action",
      render: (_: any, record: Document) => (
        <Space>
          <Button
            size="small"
            icon={<PlayCircleOutlined />}
            disabled={record.status !== "uploaded"}
            loading={ingesting === record.id}
            onClick={() => handleIngest(record.id)}
          >
            入库
          </Button>
          <Popconfirm title="确认删除？" onConfirm={() => handleDelete(record.id)}>
            <Button size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      {/* Pipeline overview */}
      <div style={{ marginBottom: 24, padding: "16px 20px", background: "#fafafa", borderRadius: 8, border: "1px solid #f0f0f0" }}>
        <Typography.Text strong style={{ fontSize: 14, marginBottom: 12, display: "block" }}>
          知识库工作流
        </Typography.Text>
        <Steps
          size="small"
          current={3}
          items={[
            { title: "上传文件", description: "支持 .txt/.md/.pdf/.docx/.xlsx" },
            { title: "入库向量化", description: "分块 → 嵌入 → Qdrant" },
            { title: "启用知识库", description: "开关打开即生效" },
            { title: "AI 自动检索", description: "提问时工具调用" },
          ]}
          style={{ maxWidth: 700 }}
        />
      </div>

      {/* Upload */}
      <div style={{ marginBottom: 16, display: "flex", alignItems: "center", gap: 12 }}>
        <Upload beforeUpload={handleUpload} showUploadList={false} accept=".txt,.md,.pdf,.docx,.doc,.xlsx">
          <Button type="primary" icon={<UploadOutlined />}>
            上传文档
          </Button>
        </Upload>
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          管理员上传文件后，先入库再启用开关即可生效
        </Typography.Text>
      </div>

      <Divider style={{ margin: "0 0 16px 0" }} />

      {/* Document table */}
      <Table
        dataSource={docs}
        columns={columns}
        rowKey="id"
        loading={loading}
        pagination={false}
        locale={{ emptyText: "暂无文档，请上传知识库文档" }}
      />

      {docs.length > 0 && (
        <div style={{ marginTop: 16, padding: "12px 16px", background: "#f6f8fa", borderRadius: 6, border: "1px solid #e8e8e8" }}>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            💡 已启用的知识库将在用户提问时由 LLM 自动检索。可在模型配置页查看全部启用状态。
          </Typography.Text>
        </div>
      )}
    </div>
  );
}
