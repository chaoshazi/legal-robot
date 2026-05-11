import { useEffect, useState, useCallback } from "react";
import {
  Card, Radio, Input, Button, Space, message, Tag, Divider, Spin, Select,
} from "antd";
import { SaveOutlined, RobotOutlined, ReloadOutlined } from "@ant-design/icons";
import type { UnifiedConfig, OllamaModelInfo } from "../../types";
import { getUnifiedConfig, updateUnifiedConfig, getOllamaModels, getOllamaEmbedModels } from "../../api/settings";

const labelStyle: React.CSSProperties = {
  marginBottom: 4,
  fontSize: 12,
  color: "#666",
};

export function ModelConfigPage() {
  const [config, setConfig] = useState<UnifiedConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);

  const [ollamaModels, setOllamaModels] = useState<OllamaModelInfo[]>([]);
  const [loadingModels, setLoadingModels] = useState(false);

  const [embedModels, setEmbedModels] = useState<OllamaModelInfo[]>([]);
  const [loadingEmbedModels, setLoadingEmbedModels] = useState(false);

  const fetchOllamaModels = useCallback(async () => {
    setLoadingModels(true);
    try {
      const [chatRes, embedRes] = await Promise.all([
        getOllamaModels(),
        getOllamaEmbedModels(),
      ]);
      if (chatRes.data) setOllamaModels(chatRes.data);
      if (embedRes.data) setEmbedModels(embedRes.data);
    } catch {
      // silent
    } finally {
      setLoadingModels(false);
    }
  }, []);

  const fetchEmbedModels = useCallback(async () => {
    setLoadingEmbedModels(true);
    try {
      const res = await getOllamaEmbedModels();
      if (res.data) setEmbedModels(res.data);
    } catch {
      // silent
    } finally {
      setLoadingEmbedModels(false);
    }
  }, []);

  const loadConfig = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getUnifiedConfig();
      if (res.data) setConfig(res.data);
    } catch {
      message.error("加载配置失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadConfig();
  }, [loadConfig]);

  useEffect(() => {
    if (config?.provider === "ollama") {
      fetchOllamaModels();
    }
  }, [config?.provider, fetchOllamaModels]);

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
      message.success("模型配置已保存，下次对话生效");
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
      <Card title={<span><RobotOutlined /> 模型提供商</span>} style={{ marginBottom: 16 }}>
        <Space direction="vertical" style={{ width: "100%" }} size="middle">
          <Radio.Group
            value={config.provider}
            onChange={(e) => update({ provider: e.target.value })}
          >
            <Radio.Button value="ollama">Ollama（本地）</Radio.Button>
            <Radio.Button value="deepseek">DeepSeek（外部 API）</Radio.Button>
          </Radio.Group>

          <Tag
            color={config.provider === "ollama" ? "blue" : "green"}
            style={{ alignSelf: "flex-start" }}
          >
            当前：{config.provider === "ollama"
              ? `Ollama — ${config.ollama_model}`
              : `DeepSeek — ${config.deepseek_model}`}
          </Tag>

          {config.provider === "ollama" ? (
            <Space align="start" wrap>
              <div>
                <div style={labelStyle}>API 地址</div>
                <Input
                  style={{ width: 320 }}
                  value={config.ollama_base_url}
                  onChange={(e) => update({ ollama_base_url: e.target.value })}
                  placeholder="http://localhost:11434"
                />
              </div>
              <div>
                <div style={labelStyle}>对话模型</div>
                <Space.Compact>
                  <Select
                    style={{ width: 240 }}
                    value={config.ollama_model}
                    onChange={(value) => update({ ollama_model: value })}
                    loading={loadingModels}
                    notFoundContent={loadingModels ? "加载中..." : "未获取到模型列表"}
                    placeholder="选择或输入模型名称"
                    showSearch
                    options={ollamaModels.map((m) => ({
                      label: `${m.name}  (${m.parameter_size}, ${m.quantization_level})`,
                      value: m.name,
                    }))}
                  />
                  <Button
                    icon={<ReloadOutlined />}
                    onClick={fetchOllamaModels}
                    loading={loadingModels}
                  />
                </Space.Compact>
              </div>
              <div>
                <div style={labelStyle}>Embedding 模型</div>
                <Space.Compact>
                  <Select
                    style={{ width: 240 }}
                    value={config.ollama_embed_model}
                    onChange={(value) => update({ ollama_embed_model: value })}
                    loading={loadingEmbedModels}
                    notFoundContent={loadingEmbedModels ? "加载中..." : "未获取到模型列表"}
                    placeholder="选择 embedding 模型"
                    showSearch
                    options={embedModels.map((m) => ({
                      label: `${m.name}  (${m.parameter_size}, ${m.quantization_level})`,
                      value: m.name,
                    }))}
                  />
                  <Button
                    icon={<ReloadOutlined />}
                    onClick={fetchEmbedModels}
                    loading={loadingEmbedModels}
                  />
                </Space.Compact>
                <div style={{ fontSize: 12, color: "#999", marginTop: 4 }}>
                  知识库入库和检索使用此模型，切换后需重建 Qdrant collection
                </div>
              </div>
            </Space>
          ) : (
            <Space direction="vertical" style={{ width: "100%" }}>
              <Space>
                <div>
                  <div style={labelStyle}>API Key</div>
                  <Input.Password
                    style={{ width: 320 }}
                    value={config.deepseek_api_key}
                    onChange={(e) => update({ deepseek_api_key: e.target.value })}
                    placeholder="sk-..."
                  />
                </div>
                <div>
                  <div style={labelStyle}>模型</div>
                  <Input
                    style={{ width: 200 }}
                    value={config.deepseek_model}
                    onChange={(e) => update({ deepseek_model: e.target.value })}
                    placeholder="deepseek-chat"
                  />
                </div>
              </Space>
              <div>
                <div style={labelStyle}>API 地址</div>
                <Input
                  style={{ width: 520 }}
                  value={config.deepseek_api_base}
                  onChange={(e) => update({ deepseek_api_base: e.target.value })}
                  placeholder="https://api.deepseek.com/v1"
                />
              </div>
            </Space>
          )}
        </Space>
      </Card>

      <Divider />

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
          保存模型配置
        </Button>
      </div>
    </div>
  );
}
