import { useEffect, useState, useCallback } from "react";
import { Card, Input, Button, Space, message, Tag, Checkbox, Divider, Spin, Typography, Select } from "antd";
import { SaveOutlined, LinkOutlined, GlobalOutlined, KeyOutlined } from "@ant-design/icons";
import type { UnifiedConfig, Tool, MCPServer, KnowledgeDocument } from "../../types";
import { getUnifiedConfig, updateUnifiedConfig } from "../../api/settings";
import { listTools } from "../../api/tools";
import { listServers } from "../../api/mcp";
import client from "../../api/client";

export function ParameterSettingsPage() {
  const [config, setConfig] = useState<UnifiedConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);

  const [tools, setTools] = useState<Tool[]>([]);
  const [mcps, setMcps] = useState<MCPServer[]>([]);
  const [knowledgeDocs, setKnowledgeDocs] = useState<KnowledgeDocument[]>([]);

  const loadAll = useCallback(async () => {
    setLoading(true);
    try {
      const [cfgRes, toolsRes, mcpsRes, kbRes] = await Promise.all([
        getUnifiedConfig(),
        listTools(),
        listServers(),
        client.get("/knowledge/documents"),
      ]);
      if (cfgRes.data) setConfig(cfgRes.data);
      if (toolsRes.data) setTools(toolsRes.data.filter((t: Tool) => t.enabled));
      if (mcpsRes.data) setMcps(mcpsRes.data.filter((m: MCPServer) => m.enabled));
      if (kbRes.data?.data) setKnowledgeDocs(kbRes.data.data);
    } catch {
      message.error("加载配置失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  const update = (patch: Partial<UnifiedConfig>) => {
    if (!config) return;
    setConfig({ ...config, ...patch });
    setDirty(true);
  };

  const handleSave = async () => {
    if (!config) return;
    setSaving(true);
    try {
      await updateUnifiedConfig(config);
      message.success("参数设置已保存，下次对话生效");
      setDirty(false);
    } catch {
      message.error("保存失败");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: 400 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!config) {
    return (
      <div style={{ padding: 24, textAlign: "center", color: "#999" }}>
        加载配置失败，请刷新重试
      </div>
    );
  }

  return (
    <div style={{ padding: 24, maxWidth: 800 }}>
      {/* Section 1: System Prompt */}
      <Card title="系统提示词" style={{ marginBottom: 16 }}>
        <Input.TextArea
          rows={8}
          value={config.system_prompt}
          onChange={(e) => update({ system_prompt: e.target.value })}
          placeholder="输入系统提示词，定义 AI 助手的身份和行为规则..."
        />
      </Card>

      {/* Section 2: Tool Bindings */}
      <Card title={<span><LinkOutlined /> 绑定工具</span>} style={{ marginBottom: 16 }}>
        {tools.length === 0 ? (
          <Typography.Text type="secondary">
            暂无可用工具，请先在<Button type="link" href="/tools" style={{ padding: "0 4px" }}>工具管理</Button>中添加
          </Typography.Text>
        ) : (
          <Checkbox.Group
            value={config.active_tool_ids}
            onChange={(values) => update({ active_tool_ids: values as string[] })}
          >
            <Space direction="vertical">
              {tools.map((t) => (
                <Checkbox key={t.id} value={t.id}>
                  <Space size={4}>
                    <span>{t.name}</span>
                    <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                      ({t.function_name})
                    </Typography.Text>
                    <Tag color="blue" style={{ fontSize: 10, lineHeight: "16px" }}>
                      {t.tool_type === "builtin" ? "内置" : "自定义"}
                    </Tag>
                  </Space>
                </Checkbox>
              ))}
            </Space>
          </Checkbox.Group>
        )}
      </Card>

      {/* Section 3: Web Search */}
      <Card
        title={<span><GlobalOutlined /> 联网搜索</span>}
        style={{ marginBottom: 16 }}
      >
        <div style={{ marginBottom: 16 }}>
          <Typography.Text strong style={{ display: "block", marginBottom: 4 }}>搜索提供商</Typography.Text>
          <Select
            value={config.web_search_provider || "duckduckgo"}
            onChange={(val) => update({ web_search_provider: val })}
            style={{ width: 240 }}
            options={[
              { value: "duckduckgo", label: "DuckDuckGo（无需配置）" },
              { value: "tavily", label: "Tavily（需 API Key）" },
            ]}
          />
        </div>

        {config.web_search_provider === "tavily" && (
          <div>
            <Typography.Text strong style={{ display: "block", marginBottom: 4 }}>Tavily API Key</Typography.Text>
            <Input.Password
              value={config.tavily_api_key}
              onChange={(e) => update({ tavily_api_key: e.target.value })}
              placeholder="输入 Tavily API Key"
              prefix={<KeyOutlined />}
              visibilityToggle
              style={{ maxWidth: 400 }}
            />
            <div style={{ marginTop: 6, fontSize: 12, color: "#999" }}>
              在 <Typography.Link href="https://tavily.com" target="_blank">Tavily 官网</Typography.Link> 注册获取 API Key
            </div>
          </div>
        )}
      </Card>

      {/* Section 4: MCP Bindings */}
      <Card title={<span><LinkOutlined /> 链接 MCP 服务</span>} style={{ marginBottom: 16 }}>
        {mcps.length === 0 ? (
          <Typography.Text type="secondary">
            暂无可用 MCP 服务，请先在<Button type="link" href="/mcp" style={{ padding: "0 4px" }}>MCP 服务</Button>中添加
          </Typography.Text>
        ) : (
          <Checkbox.Group
            value={config.active_mcp_ids}
            onChange={(values) => update({ active_mcp_ids: values as string[] })}
          >
            <Space direction="vertical">
              {mcps.map((m) => (
                <Checkbox key={m.id} value={m.id}>
                  <Space size={4}>
                    <span>{m.name}</span>
                    <Tag color="green" style={{ fontSize: 10, lineHeight: "16px" }}>
                      {m.transport.toUpperCase()}
                    </Tag>
                  </Space>
                </Checkbox>
              ))}
            </Space>
          </Checkbox.Group>
        )}
      </Card>

      {/* Section 5: Knowledge Base */}
      <Card title={<span><LinkOutlined /> 知识库</span>} style={{ marginBottom: 16 }}>
        {knowledgeDocs.length === 0 ? (
          <Typography.Text type="secondary">
            暂无知识库文档，请先在<Button type="link" href="/knowledge" style={{ padding: "0 4px" }}>知识库</Button>中上传
          </Typography.Text>
        ) : (
          <Checkbox.Group
            value={config.active_knowledge_ids}
            onChange={(values) => update({ active_knowledge_ids: values as string[] })}
          >
            <Space direction="vertical">
              {knowledgeDocs.map((d) => {
                const isIngested = d.status === "ingested";
                return (
                  <Checkbox key={d.id} value={d.id} disabled={!isIngested}>
                    <Space size={4}>
                      <span style={!isIngested ? { color: "#bbb" } : undefined}>
                        {d.filename}
                      </span>
                      <Tag
                        color={isIngested ? "success" : "default"}
                        style={{ fontSize: 10, lineHeight: "16px" }}
                      >
                        {isIngested ? "已入库" : d.status === "failed" ? "入库失败" : "待入库"}
                      </Tag>
                    </Space>
                  </Checkbox>
                );
              })}
            </Space>
          </Checkbox.Group>
        )}
      </Card>

      <Divider />

      {/* Save */}
      <div style={{ textAlign: "center" }}>
        <Button
          type="primary"
          size="large"
          icon={<SaveOutlined />}
          onClick={handleSave}
          loading={saving}
          disabled={!dirty}
          style={{ minWidth: 200 }}
        >
          保存参数设置
        </Button>
      </div>
    </div>
  );
}
