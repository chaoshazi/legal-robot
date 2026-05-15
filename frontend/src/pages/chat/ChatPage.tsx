import { useState, useRef, useEffect, useCallback } from "react";
import {
  Input,
  Button,
  Typography,
  Spin,
  Space,
  Select,
  Popconfirm,
  message,
  Modal,
  Tag,
  Collapse,
  Switch,
  Avatar,
} from "antd";
import {
  SendOutlined,
  RobotOutlined,
  UserOutlined,
  DeleteOutlined,
  PlusOutlined,
  EditOutlined,
  SearchOutlined,
  GlobalOutlined,
  ClockCircleOutlined,
  CalculatorOutlined,
  BulbOutlined,
  ArrowDownOutlined,
  PaperClipOutlined,
  CloseCircleOutlined,
  FileOutlined,
} from "@ant-design/icons";
import { Upload } from "antd";
import type { UploadFile } from "antd";
import { chatApi } from "../../api/chat";
import { getUnifiedConfig } from "../../api/settings";
import { useAuthStore } from "../../stores/authStore";
import { MarkdownContent } from "../../components/MarkdownContent";
import { VoiceRecorder } from "../../components/chat/VoiceRecorder";
import { ImagePreview } from "../../components/chat/ImagePreview";
import { AudioPlayer } from "../../components/chat/AudioPlayer";
import { FileAttachment } from "../../components/chat/FileAttachment";
import { uploadApi, type UploadResult } from "../../api/upload";

interface Source {
  law: string;
  article: string;
  text: string;
}

interface Attachment {
  id: string;
  file_type: "image" | "document" | "audio";
  filename: string;
  file_size: number;
  mime_type: string;
  extracted_text?: string;
  transcription?: string;
  status: string;
  url?: string;
  created_at: string;
}

interface Message {
  role: "user" | "assistant";
  content: string;
  reasoning?: string;
  sources?: Source[];
  attachments?: Attachment[];
}

interface PendingAttachment {
  id: string;
  filename: string;
  file_type: string;
  file_size: number;
  status: string;
  url?: string;
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
  const [showScrollBtn, setShowScrollBtn] = useState(false);
  const [pendingAttachments, setPendingAttachments] = useState<PendingAttachment[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const sendingRef = useRef(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent]);

  useEffect(() => {
    loadSessions();
  }, []);

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

  // Scroll to bottom button visibility
  const handleScroll = useCallback(() => {
    if (!containerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    setShowScrollBtn(scrollHeight - scrollTop - clientHeight > 200);
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
            attachments: m.attachments || [],
          }))
        );
      }
    } catch {
      // ignore
    }
  };

  const handleFileUpload = async (file: File): Promise<false> => {
    try {
      const { data } = await uploadApi.upload(file, currentSessionId || undefined);
      if (data.data) {
        setPendingAttachments((prev) => [...prev, {
          id: data.data!.id,
          filename: data.data!.filename,
          file_type: data.data!.file_type,
          file_size: data.data!.file_size,
          status: data.data!.status,
          url: data.data!.url,
        }]);
        if (data.data.file_type === "audio" && data.data.status === "uploaded") {
          // Auto-transcribe will happen via VoiceRecorder separately
        } else if (data.data.status === "ready") {
          message.success(`${file.name} 已就绪`);
        }
      }
    } catch {
      message.error(`上传失败: ${file.name}`);
    }
    return false; // prevent default Upload behavior
  };

  const removePendingAttachment = (id: string) => {
    setPendingAttachments((prev) => prev.filter((a) => a.id !== id));
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
    if ((!input.trim() && pendingAttachments.length === 0) || loading || sendingRef.current) return;
    sendingRef.current = true;
    const question = input.trim();
    const attachmentIds = pendingAttachments.map((a) => a.id);
    setInput("");
    setPendingAttachments([]);
    setMessages((prev) => [...prev, { role: "user", content: question, attachments: pendingAttachments.map((a) => ({
      id: a.id,
      file_type: a.file_type as "image" | "document" | "audio",
      filename: a.filename,
      file_size: a.file_size,
      mime_type: "",
      status: a.status,
      created_at: "",
    })) }]);
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
        body: JSON.stringify({ session_id: sessionId, content: question, enable_web_search: webSearchEnabled, attachment_ids: attachmentIds }),
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
  }, [input, loading, currentSessionId, webSearchEnabled, pendingAttachments]);

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
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "calc(100vh - 64px)",
        background: "var(--bg)",
      }}
    >
      {/* Session toolbar */}
      <div
        style={{
          padding: "12px 24px",
          background: "rgba(255,255,255,0.9)",
          backdropFilter: "blur(8px)",
          borderBottom: "1px solid var(--border)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: 8,
        }}
      >
        <Space wrap>
          <Select
            style={{ width: 220 }}
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
              <Button icon={<EditOutlined />} onClick={() => {
                const s = sessions.find((x) => x.id === currentSessionId);
                setRenameValue(s?.title ?? "");
                setRenameModalOpen(true);
              }}>
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

        {/* Web search toggle */}
        <Space size={4}>
          <GlobalOutlined style={{ color: webSearchEnabled ? "#2563eb" : "#94a3b8", fontSize: 14 }} />
          <Typography.Text style={{ fontSize: 13, color: "var(--text-secondary)" }}>
            联网搜索
          </Typography.Text>
          <Switch
            checked={webSearchEnabled}
            onChange={setWebSearchEnabled}
            checkedChildren="开"
            unCheckedChildren="关"
            size="small"
          />
        </Space>
      </div>

      {/* Messages area */}
      <div
        ref={containerRef}
        onScroll={handleScroll}
        style={{
          flex: 1,
          overflow: "auto",
          padding: "24px 0",
          position: "relative",
        }}
      >
        <div style={{ maxWidth: 800, margin: "0 auto", padding: "0 24px" }}>
          {/* Empty state */}
          {visibleMessages.length === 0 && (
            <div
              style={{
                textAlign: "center",
                marginTop: 120,
                color: "var(--text-secondary)",
              }}
            >
              <div
                style={{
                  width: 72,
                  height: 72,
                  borderRadius: "50%",
                  background: "linear-gradient(135deg, rgba(37,99,235,0.08), rgba(124,58,237,0.08))",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  margin: "0 auto 20px",
                }}
              >
                <RobotOutlined style={{ fontSize: 32, color: "var(--primary)" }} />
              </div>
              <Typography.Title level={3} style={{ color: "var(--text)", fontWeight: 600, marginBottom: 8 }}>
                AI 法律咨询
              </Typography.Title>
              <Typography.Text style={{ color: "var(--text-secondary)", fontSize: 15, display: "block", marginBottom: 32 }}>
                您好！我是智能法律助手，请描述您的法律问题
              </Typography.Text>
              <div style={{ display: "flex", justifyContent: "center", gap: 12, flexWrap: "wrap" }}>
                {["劳动合同纠纷", "婚姻家庭问题", "房产交易咨询", "公司股权事项"].map((topic) => (
                  <div
                    key={topic}
                    onClick={() => setInput(topic)}
                    style={{
                      padding: "8px 16px",
                      borderRadius: 20,
                      border: "1px solid var(--border)",
                      cursor: "pointer",
                      fontSize: 13,
                      color: "var(--text-secondary)",
                      transition: "all 0.2s",
                      background: "#fff",
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.borderColor = "#2563eb";
                      e.currentTarget.style.color = "#2563eb";
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.borderColor = "var(--border)";
                      e.currentTarget.style.color = "var(--text-secondary)";
                    }}
                  >
                    {topic}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Messages */}
          {visibleMessages.map((msg, i) => (
            <div
              key={i}
              style={{
                display: "flex",
                marginBottom: 20,
                gap: 12,
                flexDirection: msg.role === "user" ? "row-reverse" : "row",
                alignItems: "flex-start",
              }}
            >
              {/* Avatar */}
              <Avatar
                size={36}
                style={{
                  flexShrink: 0,
                  background: msg.role === "user"
                    ? "linear-gradient(135deg, #2563eb, #1d4ed8)"
                    : "linear-gradient(135deg, #10b981, #059669)",
                  boxShadow: msg.role === "user"
                    ? "0 2px 8px rgba(37,99,235,0.3)"
                    : "0 2px 8px rgba(16,185,129,0.3)",
                }}
                icon={msg.role === "user" ? <UserOutlined /> : <RobotOutlined />}
              />

              {/* Bubble */}
              <div style={{ maxWidth: "72%", minWidth: 0 }}>
                <div
                  style={{
                    padding: "14px 18px",
                    borderRadius: msg.role === "user"
                      ? "18px 18px 4px 18px"
                      : "18px 18px 18px 4px",
                    background: msg.role === "user"
                      ? "linear-gradient(135deg, #2563eb, #1d4ed8)"
                      : "#ffffff",
                    color: msg.role === "user" ? "#fff" : "var(--text)",
                    boxShadow: msg.role === "user"
                      ? "0 2px 8px rgba(37,99,235,0.2)"
                      : "0 1px 4px rgba(0,0,0,0.06)",
                    fontSize: 14,
                    lineHeight: 1.7,
                    wordBreak: "break-word",
                  }}
                >
                  {msg.role === "user" ? (
                    <>
                      {msg.attachments?.map((att) => (
                        <div key={att.id} style={{ marginBottom: 6 }}>
                          {att.file_type === "image" && att.url && (
                            <ImagePreview src={att.url} filename={att.filename} />
                          )}
                          {att.file_type === "audio" && (
                            <AudioPlayer src={uploadApi.getDownloadUrl(att.id)} />
                          )}
                          {att.file_type === "document" && (
                            <FileAttachment
                              filename={att.filename}
                              fileSize={att.file_size}
                              fileType={att.mime_type}
                              downloadUrl={uploadApi.getDownloadUrl(att.id)}
                            />
                          )}
                        </div>
                      ))}
                      {msg.content && <div style={{ whiteSpace: "pre-wrap" }}>{msg.content}</div>}
                    </>
                  ) : (
                    <MarkdownContent content={msg.content} />
                  )}
                </div>
              </div>
            </div>
          ))}

          {/* Streaming reasoning */}
          {loading && streamingReasoning && (
            <div style={{ display: "flex", marginBottom: 16, gap: 12, alignItems: "flex-start" }}>
              <Avatar size={36} style={{ flexShrink: 0, background: "linear-gradient(135deg, #10b981, #059669)", boxShadow: "0 2px 8px rgba(16,185,129,0.3)" }} icon={<RobotOutlined />} />
              <div style={{ maxWidth: "72%" }}>
                <Collapse
                  ghost
                  size="small"
                  defaultActiveKey="reasoning"
                  style={{
                    background: "#f8fafc",
                    borderRadius: 8,
                    border: "1px solid #e2e8f0",
                  }}
                  items={[{
                    key: "reasoning",
                    label: (
                      <span style={{ fontSize: 13 }}>
                        <BulbOutlined style={{ marginRight: 6, color: "#f59e0b" }} />
                        思考过程
                      </span>
                    ),
                    children: (
                      <div style={{ whiteSpace: "pre-wrap", fontSize: 13, color: "#64748b" }}>
                        {streamingReasoning}
                      </div>
                    ),
                  }]}
                />
              </div>
            </div>
          )}

          {/* Committed reasoning */}
          {!loading && lastReasoning && (
            <div style={{ display: "flex", marginBottom: 16, gap: 12, alignItems: "flex-start" }}>
              <Avatar size={36} style={{ flexShrink: 0, background: "linear-gradient(135deg, #10b981, #059669)", boxShadow: "0 2px 8px rgba(16,185,129,0.3)" }} icon={<RobotOutlined />} />
              <div style={{ maxWidth: "72%" }}>
                <Collapse
                  ghost
                  size="small"
                  style={{
                    background: "#f8fafc",
                    borderRadius: 8,
                    border: "1px solid #e2e8f0",
                  }}
                  items={[{
                    key: "reasoning",
                    label: (
                      <span style={{ fontSize: 13 }}>
                        <BulbOutlined style={{ marginRight: 6, color: "#f59e0b" }} />
                        思考过程
                      </span>
                    ),
                    children: (
                      <div style={{ whiteSpace: "pre-wrap", fontSize: 13, color: "#64748b" }}>
                        {lastReasoning}
                      </div>
                    ),
                  }]}
                />
              </div>
            </div>
          )}

          {/* Active tools */}
          {activeTools.length > 0 && (
            <div style={{ display: "flex", marginBottom: 16, gap: 12, alignItems: "flex-start" }}>
              <Avatar size={36} style={{ flexShrink: 0, background: "linear-gradient(135deg, #10b981, #059669)", boxShadow: "0 2px 8px rgba(16,185,129,0.3)" }} icon={<RobotOutlined />} />
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center" }}>
                <Spin size="small" />
                {activeTools.map((t) => {
                  const toolConfig: Record<string, { label: string; icon: React.ReactNode; color: string }> = {
                    search_knowledge_base: { label: "检索知识库...", icon: <SearchOutlined />, color: "blue" },
                    web_search: { label: "搜索互联网...", icon: <GlobalOutlined />, color: "geekblue" },
                    get_current_datetime: { label: "获取时间...", icon: <ClockCircleOutlined />, color: "orange" },
                    calculate: { label: "计算中...", icon: <CalculatorOutlined />, color: "purple" },
                    calculate_compensation: { label: "计算赔偿...", icon: <CalculatorOutlined />, color: "purple" },
                  };
                  const cfg = toolConfig[t] ?? { label: `调用工具: ${t}`, icon: <SearchOutlined />, color: "blue" };
                  return <Tag key={t} icon={cfg.icon} color={cfg.color}>{cfg.label}</Tag>;
                })}
              </div>
            </div>
          )}

          {/* Initial loading state */}
          {loading && !streamingContent && activeTools.length === 0 && (
            <div style={{ display: "flex", marginBottom: 16, gap: 12, alignItems: "flex-start" }}>
              <Avatar size={36} style={{ flexShrink: 0, background: "linear-gradient(135deg, #10b981, #059669)", boxShadow: "0 2px 8px rgba(16,185,129,0.3)" }} icon={<RobotOutlined />} />
              <div
                style={{
                  padding: "14px 20px",
                  borderRadius: "18px 18px 18px 4px",
                  background: "#ffffff",
                  boxShadow: "0 1px 4px rgba(0,0,0,0.06)",
                }}
              >
                <span style={{ color: "var(--text-secondary)", fontSize: 14 }}>AI 正在思考</span>
                <span className="thinking-dots" />
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Scroll to bottom button */}
        {showScrollBtn && (
          <div style={{ position: "sticky", bottom: 16, textAlign: "center", pointerEvents: "none" }}>
            <Button
              shape="circle"
              icon={<ArrowDownOutlined />}
              onClick={() => bottomRef.current?.scrollIntoView({ behavior: "smooth" })}
              style={{ pointerEvents: "auto", boxShadow: "0 2px 8px rgba(0,0,0,0.15)" }}
            />
          </div>
        )}
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

      {/* Input area */}
      <div
        style={{
          borderTop: "1px solid var(--border)",
          padding: "12px 24px 16px",
          background: "rgba(255,255,255,0.95)",
          backdropFilter: "blur(8px)",
        }}
      >
        <div style={{ maxWidth: 800, margin: "0 auto" }}>
          {/* Pending attachments preview */}
          {pendingAttachments.length > 0 && (
            <div
              style={{
                display: "flex",
                gap: 8,
                marginBottom: 10,
                flexWrap: "wrap",
              }}
            >
              {pendingAttachments.map((att) => (
                <div
                  key={att.id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                    padding: "4px 8px 4px 10px",
                    background: "#f1f5f9",
                    borderRadius: 8,
                    border: "1px solid #e2e8f0",
                    fontSize: 12,
                  }}
                >
                  <FileOutlined style={{ color: "#64748b" }} />
                  <span style={{ color: "var(--text)", maxWidth: 160, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {att.filename}
                  </span>
                  <span style={{ color: att.status === "ready" ? "#16a34a" : "#f59e0b", fontSize: 11 }}>
                    {att.status === "ready" ? "就绪" : "处理中"}
                  </span>
                  <CloseCircleOutlined
                    style={{ color: "#94a3b8", cursor: "pointer", flexShrink: 0 }}
                    onClick={() => removePendingAttachment(att.id)}
                  />
                </div>
              ))}
            </div>
          )}

          <div
            style={{
              display: "flex",
              gap: 12,
              background: "var(--bg)",
              borderRadius: 12,
              padding: "4px 4px 4px 4px",
              border: "1px solid var(--border)",
              transition: "border-color 0.2s, box-shadow 0.2s",
              alignItems: "center",
            }}
            onFocusCapture={(e) => {
              const parent = e.currentTarget;
              parent.style.borderColor = "#2563eb";
              parent.style.boxShadow = "0 0 0 3px rgba(37,99,235,0.1)";
            }}
            onBlurCapture={(e) => {
              const parent = e.currentTarget;
              parent.style.borderColor = "var(--border)";
              parent.style.boxShadow = "none";
            }}
          >
            {/* Upload button */}
            <Upload
              beforeUpload={handleFileUpload}
              showUploadList={false}
              accept=".pdf,.docx,.doc,.xlsx,.txt,.jpg,.jpeg,.png,.webp,.wav,.mp3,.webm"
              disabled={loading}
            >
              <Button
                type="default"
                icon={<PaperClipOutlined style={{ fontSize: 16 }} />}
                disabled={loading}
                style={{ marginLeft: 4, display: "inline-flex", alignItems: "center", justifyContent: "center" }}
              />
            </Upload>

            {/* Voice recorder */}
            <VoiceRecorder
              sessionId={currentSessionId}
              onTranscription={(text) => setInput((prev) => prev + text)}
              disabled={loading}
            />

            <Input
              size="large"
              placeholder="请输入您的法律问题..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onPressEnter={handleSend}
              disabled={loading}
              variant="borderless"
              style={{ fontSize: 14, padding: "8px 0", flex: 1 }}
            />
            <Button
              type="primary"
              icon={<SendOutlined />}
              onClick={handleSend}
              loading={loading}
              style={{
                height: 44,
                width: 44,
                borderRadius: 10,
                flexShrink: 0,
              }}
            />
          </div>
          <div style={{ marginTop: 8, fontSize: 12, color: "#94a3b8", textAlign: "center" }}>
            AI 生成内容仅供参考，不构成法律意见
          </div>
        </div>
      </div>
    </div>
  );
}
