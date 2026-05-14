import { useState, useRef, useEffect, useCallback } from "react";
import { Input, Button, Typography, Spin, Space, Select, Popconfirm, message, Modal, Tag, Collapse, Switch } from "antd";
import { SendOutlined, RobotOutlined, UserOutlined, DeleteOutlined, PlusOutlined, EditOutlined, SearchOutlined, GlobalOutlined, ClockCircleOutlined, CalculatorOutlined, BulbOutlined } from "@ant-design/icons";
import { chatApi } from "../../api/chat";
import { getUnifiedConfig } from "../../api/settings";

interface Source {
  law: string;
  article: string;
  text: string;
}

interface Message {
  role: "user" | "assistant";
  content: string;
  reasoning?: string;
  sources?: Source[];
}

interface SessionOption {
  id: string;
  title: string;
}

export function ChatPage() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [sessions, setSessions] = useState<SessionOption[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [streamingContent, setStreamingContent] = useState("");
  const [streamingReasoning, setStreamingReasoning] = useState("");
  const [activeTools, setActiveTools] = useState<string[]>([]);
  const [renameModalOpen, setRenameModalOpen] = useState(false);
  const [renameValue, setRenameValue] = useState("");
  const [lastReasoning, setLastReasoning] = useState("");
  const [webSearchEnabled, setWebSearchEnabled] = useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const sendingRef = useRef(false);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent]);

  // Load sessions on mount
  useEffect(() => {
    loadSessions();
  }, []);

  // Load initial web search toggle state from saved config
  useEffect(() => {
    (async () => {
      try {
        const { data } = await getUnifiedConfig();
        if (data?.active_tool_ids) {
          setWebSearchEnabled(data.active_tool_ids.includes("builtin:web_search"));
        }
      } catch {
        // default to true
      }
    })();
  }, []);

  const loadSessions = async () => {
    try {
      const { data } = await chatApi.listSessions();
      if (data.data) {
        const list = data.data.map((s: any) => ({ id: s.id, title: s.title }));
        setSessions(list);
      }
    } catch {
      // ignore
    }
  };

  const loadMessages = async (sessionId: string) => {
    try {
      const { data } = await chatApi.getMessages(sessionId);
      if (data.data) {
        setMessages(
          (data.data as any[]).map((m) => ({
            role: m.role as "user" | "assistant",
            content: m.content,
          }))
        );
      }
    } catch {
      // ignore
    }
  };

  const ensureSession = async (): Promise<string> => {
    if (currentSessionId) return currentSessionId;
    const { data } = await chatApi.createSession({ title: "新会话" });
    if (data.data) {
      setCurrentSessionId(data.data.id);
      setSessions((prev) => [...prev, { id: data.data!.id, title: data.data!.title }]);
      return data.data.id;
    }
    throw new Error("Failed to create session");
  };

  const handleSend = useCallback(async () => {
    if (!input.trim() || loading || sendingRef.current) return;
    sendingRef.current = true;
    const question = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setLoading(true);
    setStreamingContent("");
    setLastReasoning("");

    try {
      const sessionId = await ensureSession();
      const token = localStorage.getItem("access_token");
      abortRef.current = new AbortController();

      const response = await fetch("/api/v1/chat/stream", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ session_id: sessionId, content: question, enable_web_search: webSearchEnabled }),
        signal: abortRef.current.signal,
      });

      if (!response.ok) throw new Error("Stream request failed");

      const reader = response.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let fullContent = "";
      let fullReasoning = "";
      let toolCalls: string[] = [];

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const payload = JSON.parse(line.slice(6));

          if (payload.error) {
            throw new Error(payload.error);
          }

          if (payload.done) {
            const committedReasoning = payload.reasoning || fullReasoning;
            setLastReasoning(committedReasoning);
            setMessages((prev) => [...prev, { role: "assistant", content: fullContent, reasoning: committedReasoning }]);
            setStreamingContent("");
            setStreamingReasoning("");
            setActiveTools([]);
          } else if (payload.reasoning) {
            fullReasoning += payload.reasoning || "";
            setStreamingReasoning(fullReasoning);
          } else if (payload.tool_start) {
            toolCalls.push(payload.tool_start);
            setActiveTools([...toolCalls]);
            fullReasoning += `[调用工具: ${payload.tool_start}]\n`;
            setStreamingReasoning(fullReasoning);
          } else if (payload.tool_end) {
            toolCalls = toolCalls.filter((t) => t !== payload.tool_end);
            setActiveTools([...toolCalls]);
          } else {
            fullContent += payload.token || "";
            setStreamingContent(fullContent);
          }
        }
      }
    } catch (err: any) {
      if (err.name !== "AbortError") {
        const detail = err.message || "未知错误";
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: `抱歉，服务异常：${detail}` },
        ]);
      }
    } finally {
      setLoading(false);
      setStreamingContent("");
      setStreamingReasoning("");
      abortRef.current = null;
      sendingRef.current = false;
    }
  }, [input, loading, currentSessionId]);

  const handleSessionChange = (sessionId: string) => {
    setCurrentSessionId(sessionId);
    setMessages([]);
    loadMessages(sessionId);
  };

  const handleDeleteSession = async (sessionId: string) => {
    try {
      await chatApi.deleteSession(sessionId);
      message.success("会话已删除");
      const newSessions = sessions.filter((s) => s.id !== sessionId);
      setSessions(newSessions);
      if (currentSessionId === sessionId) {
        if (newSessions.length > 0) {
          setCurrentSessionId(newSessions[0].id);
          setMessages([]);
          loadMessages(newSessions[0].id);
        } else {
          setCurrentSessionId(null);
          setMessages([]);
        }
      }
    } catch {
      message.error("删除失败");
    }
  };

  const handleRename = async () => {
    if (!currentSessionId || !renameValue.trim()) return;
    try {
      const { data } = await chatApi.renameSession(currentSessionId, renameValue.trim());
      if (data.data) {
        setSessions((prev) =>
          prev.map((s) => (s.id === currentSessionId ? { ...s, title: data.data!.title } : s))
        );
        message.success("重命名成功");
      }
    } catch {
      message.error("重命名失败");
    } finally {
      setRenameModalOpen(false);
    }
  };

  const visibleMessages = [
    ...messages,
    ...(loading && streamingContent
      ? [{ role: "assistant" as const, content: streamingContent }]
      : []),
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "calc(100vh - 64px)" }}>
      {/* Session selector */}
      <div style={{ padding: "12px 24px", borderBottom: "1px solid #f0f0f0" }}>
        <Space>
          <Select
            style={{ width: 240 }}
            placeholder="选择会话"
            value={currentSessionId}
            onChange={handleSessionChange}
            options={sessions.map((s) => ({ value: s.id, label: s.title }))}
          />
          <Button
            icon={<PlusOutlined />}
            onClick={async () => {
              const { data } = await chatApi.createSession({ title: "新会话" });
              if (data.data) {
                setCurrentSessionId(data.data.id);
                setMessages([]);
                setSessions((prev) => [...prev, { id: data.data!.id, title: data.data!.title }]);
              }
            }}
          >
            新建会话
          </Button>
          {currentSessionId && (
            <>
              <Button
                icon={<EditOutlined />}
                onClick={() => {
                  const s = sessions.find((x) => x.id === currentSessionId);
                  setRenameValue(s?.title ?? "");
                  setRenameModalOpen(true);
                }}
              >
                重命名
              </Button>
              <Popconfirm
                title="确认删除该会话？会话中的消息也将被删除。"
                onConfirm={() => handleDeleteSession(currentSessionId!)}
              >
                <Button danger icon={<DeleteOutlined />}>
                  删除会话
                </Button>
              </Popconfirm>
            </>
          )}
        </Space>
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflow: "auto", padding: "24px" }}>
        {visibleMessages.length === 0 && (
          <div style={{ textAlign: "center", marginTop: 120, color: "#999" }}>
            <RobotOutlined style={{ fontSize: 48, marginBottom: 16 }} />
            <Typography.Title level={4} type="secondary">
              法律咨询机器人
            </Typography.Title>
            <Typography.Text type="secondary">
              请输入您的法律问题
            </Typography.Text>
          </div>
        )}
        {visibleMessages.map((msg, i) => (
          <div
            key={i}
            style={{
              display: "flex",
              flexDirection: "column",
              marginBottom: 16,
              alignItems: msg.role === "user" ? "flex-end" : "flex-start",
            }}
          >
            <div
              style={{
                maxWidth: "70%",
                padding: "12px 16px",
                borderRadius: 8,
                background: msg.role === "user" ? "#1677ff" : "#f5f5f5",
                color: msg.role === "user" ? "#fff" : "#000",
              }}
            >
              <div style={{ marginBottom: 4 }}>
                {msg.role === "user" ? <UserOutlined /> : <RobotOutlined />}
                <strong style={{ marginLeft: 4 }}>
                  {msg.role === "user" ? "我" : "AI"}
                </strong>
              </div>
              <div style={{ whiteSpace: "pre-wrap" }}>{msg.content}</div>
            </div>
          </div>
        ))}
        {loading && streamingReasoning && (
          <div style={{ maxWidth: "70%", marginBottom: 16 }}>
            <Collapse
              ghost
              size="small"
              defaultActiveKey="reasoning"
              style={{ background: "#fafafa", borderRadius: 4 }}
              items={[{
                key: "reasoning",
                label: <span><BulbOutlined /> 思考过程</span>,
                children: <div style={{ whiteSpace: "pre-wrap", fontSize: 13, color: "#666" }}>{streamingReasoning}</div>,
              }]}
            />
          </div>
        )}
        {!loading && lastReasoning && (
          <div style={{ maxWidth: "70%", marginBottom: 16 }}>
            <Collapse
              ghost
              size="small"
              defaultActiveKey="reasoning"
              style={{ background: "#fafafa", borderRadius: 4 }}
              items={[{
                key: "reasoning",
                label: <span><BulbOutlined /> 思考过程</span>,
                children: <div style={{ whiteSpace: "pre-wrap", fontSize: 13, color: "#666" }}>{lastReasoning}</div>,
              }]}
            />
          </div>
        )}
        {activeTools.length > 0 && (
          <div style={{ textAlign: "center", padding: "8px 16px" }}>
            <Space>
              <Spin size="small" />
              {activeTools.map((t) => {
                const toolConfig: Record<string, { label: string; icon: React.ReactNode; color: string }> = {
                  search_knowledge_base: { label: "正在检索知识库...", icon: <SearchOutlined />, color: "blue" },
                  web_search: { label: "正在搜索互联网...", icon: <GlobalOutlined />, color: "geekblue" },
                  get_current_datetime: { label: "正在获取时间...", icon: <ClockCircleOutlined />, color: "orange" },
                  calculate: { label: "正在计算...", icon: <CalculatorOutlined />, color: "purple" },
                  calculate_compensation: { label: "正在计算赔偿...", icon: <CalculatorOutlined />, color: "purple" },
                };
                const cfg = toolConfig[t] ?? { label: `调用工具: ${t}`, icon: <SearchOutlined />, color: "blue" };
                return <Tag key={t} icon={cfg.icon} color={cfg.color}>{cfg.label}</Tag>;
              })}
            </Space>
          </div>
        )}
        {loading && !streamingContent && activeTools.length === 0 && (
          <div style={{ textAlign: "center", padding: 16 }}>
            <Spin tip="AI 正在思考..." />
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Rename modal */}
      <Modal
        title="重命名会话"
        open={renameModalOpen}
        onOk={handleRename}
        onCancel={() => setRenameModalOpen(false)}
        okText="保存"
        cancelText="取消"
      >
        <Input
          value={renameValue}
          onChange={(e) => setRenameValue(e.target.value)}
          onPressEnter={handleRename}
          placeholder="输入新会话名称"
        />
      </Modal>

      {/* Web search toggle */}
      <div style={{ borderTop: "1px solid #f0f0f0", padding: "6px 24px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          <GlobalOutlined style={{ marginRight: 4, color: webSearchEnabled ? "#1677ff" : "#999" }} />
          联网搜索
        </Typography.Text>
        <Switch
          checked={webSearchEnabled}
          onChange={setWebSearchEnabled}
          checkedChildren="已开启"
          unCheckedChildren="已关闭"
          size="small"
        />
      </div>

      {/* Input */}
      <div style={{ borderTop: "1px solid #f0f0f0", padding: "16px 24px" }}>
        <Space.Compact style={{ width: "100%" }}>
          <Input
            size="large"
            placeholder="请输入您的法律问题..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onPressEnter={handleSend}
            disabled={loading}
          />
          <Button
            type="primary"
            size="large"
            icon={<SendOutlined />}
            onClick={handleSend}
            loading={loading}
          >
            发送
          </Button>
        </Space.Compact>
        <div style={{ marginTop: 8, fontSize: 12, color: "#999", textAlign: "center" }}>
          *AI 生成内容仅供参考，不构成法律意见
        </div>
      </div>
    </div>
  );
}
