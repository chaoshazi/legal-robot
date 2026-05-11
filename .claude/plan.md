# 对外 MCP SSE 服务 — 外部调用指南

## 1. 凭据准备

### 1.1 JWT Token（必需）

所有调用方必须先获取一个 JWT `access_token`。通过系统已有的登录接口获取：

```bash
# 登录获取 token
curl -s -X POST http://<host>:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "your_password"}' | jq .
```

返回示例：
```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer"
  }
}
```

**凭据说明：**
- **凭据名称**：`access_token`（JWT Bearer Token）
- **有效期**：由系统配置 `access_token_expire_minutes` 控制（默认 480 分钟）
- **续期方式**：调用 `POST /api/v1/auth/refresh` 使用 `refresh_token` 换取新 `access_token`
- **所需角色**：任意已激活用户均可（user / lawyer / admin）
- **Token 负载包含**：用户 ID（`sub`）、角色（`role`）、过期时间（`exp`）、类型（`type=access`）

---

## 2. MCP 客户端配置

### 2.1 Claude Desktop 配置

编辑 `claude_desktop_config.json`：

```json
{
  "mcpServers": {
    "legal-consult": {
      "transport": "sse",
      "url": "http://your-host:8000/api/v1/external-mcp/sse?token=eyJhbGciOiJIUzI1NiIs..."
    }
  }
}
```

**重要：** Token 必须拼在 SSE URL 的 `?token=` 查询参数上。如果 Token 过期，需要重新配置新的 Token 并重启 Claude Desktop。

### 2.2 Cursor 配置

在 Cursor 中：
1. 打开 Settings → Features → MCP Servers
2. 点击 "Add new MCP Server"
3. 填写：
   - **Name**: `legal-consult`
   - **Type**: `sse`
   - **Url**: `http://your-host:8000/api/v1/external-mcp/sse?token=eyJhbGciOiJIUzI1NiIs...`
4. 点击 Save

### 2.3 自定义 MCP 客户端（Python）

```python
from mcp import ClientSession
from mcp.client.sse import sse_client

# 1. 先登录获取 token
# ...

# 2. 建立 SSE 连接并初始化 MCP 会话
async with sse_client(
    url="http://your-host:8000/api/v1/external-mcp/sse",
    headers={},
    token="eyJhbGciOiJIUzI1NiIs..."  # 如果 SDK 不支持此参数，拼在 URL 上
) as streams:
    async with ClientSession(streams[0], streams[1]) as session:
        # 初始化
        await session.initialize()
        
        # 列出可用工具
        tools = await session.list_tools()
        for tool in tools.tools:
            print(f"{tool.name}: {tool.description}")
        
        # 调用工具
        result = await session.call_tool(
            "search_knowledge",
            {"query": "劳动合同解除经济补偿", "top_k": 3}
        )
        print(result.content)
```

### 2.4 TypeScript / Node.js 客户端

```typescript
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { SSEClientTransport } from "@modelcontextprotocol/sdk/client/sse.js";

const transport = new SSEClientTransport(
  new URL(
    "http://your-host:8000/api/v1/external-mcp/sse?token=eyJhbGciOiJIUzI1NiIs..."
  )
);

const client = new Client(
  { name: "legal-consult-client", version: "1.0.0" },
  { capabilities: {} }
);

await client.connect(transport);

// 列出工具
const tools = await client.listTools();
console.log(tools);

// 调用工具
const result = await client.callTool({
  name: "legal_query",
  arguments: {
    question: "在上班途中发生交通事故算工伤吗？"
  }
});
console.log(result.content);
```

---

## 3. 可用工具详情

### 3.1 `legal_query` — 法律咨询提问

**功能：** 向法律咨询 AI 提问，自动检索知识库并生成专业回答，同时创建咨询单记录。

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `question` | string | 是 | 法律咨询问题，应清晰描述事实 |
| `session_id` | string | 否 | 会话 ID，传入后可保持多轮对话上下文连续 |

**返回：** 纯文本（Markdown 格式的回答），末尾自动追加法律免责声明。

**调用示例（Claude Desktop 中）：**
```
请帮我咨询一个法律问题：在上班途中发生交通事故算工伤吗？
```
Claude Desktop 会自动调用 `legal_query` 工具并展示结果。

**session_id 使用场景（多轮对话）：**
```
第一轮：
legal_query(question="朋友借了10万不还怎么办？")
→ 返回结果中建议找回复的 session_id（日志中可查看）

第二轮：
legal_query(question="如果他有房产但不愿意卖房还款呢？", session_id="上一步返回的ID")
→ AI 能记住上轮对话上下文
```

### 3.2 `search_knowledge` — 知识库检索

**功能：** 检索法律知识库中的相关法规条文，支持向量语义搜索和法条编号精确匹配。

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `query` | string | 是 | 搜索关键词或法律问题描述 |
| `top_k` | number | 否 | 返回结果数量，默认 5，范围 1-20 |

**返回：** JSON 字符串
```json
{
  "results": [
    {
      "content": "……条文原文……",
      "source": "中华人民共和国劳动合同法",
      "doc_id": "uuid-xxx"
    }
  ],
  "total": 3
}
```

### 3.3 `get_consultation` — 查询咨询单

**功能：** 查询法律咨询单的详细信息和当前审核状态。

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `consultation_id` | string | 是 | 咨询单 UUID |

**返回：** JSON 字符串
```json
{
  "id": "uuid-xxx",
  "question": "问题描述",
  "draft_answer": "AI 生成的草稿回答",
  "final_answer": "律师审核后的最终回答",
  "status": "draft|published|rejected",
  "review_comment": "律师审核意见",
  "created_at": "创建时间",
  "reviewed_at": "审核时间"
}
```

### 3.4 `list_knowledge_documents` — 知识库文档列表

**功能：** 列出知识库中所有文档及处理状态。

**参数：** 无

**返回：** JSON 字符串
```json
{
  "documents": [
    {
      "id": "uuid-xxx",
      "filename": "民法典.pdf",
      "file_size": 1024000,
      "chunk_count": 150,
      "status": "completed",
      "error": null,
      "created_at": "2025-01-01T00:00:00+00:00"
    }
  ],
  "total": 10
}
```

---

## 4. 典型使用流程

```
┌─────────────┐     ┌──────────────────────┐     ┌─────────────┐
│  外部客户端  │────▶│  法律咨询 MCP SSE     │────▶│  PostgreSQL  │
│ (Claude/    │     │  /api/v1/external-   │     │  Qdrant      │
│  Cursor/    │◀────│  mcp/sse             │◀────│  LLM Agent   │
│  自定义)    │     └──────────────────────┘     └─────────────┘
```

**Step 1: 获取凭证**
```
POST /api/v1/auth/login → 得到 access_token
```

**Step 2: 配置 MCP 客户端**
```
MCP SSE URL = http://host:8000/api/v1/external-mcp/sse?token=<access_token>
```

**Step 3: 调用工具**
```
客户端发送 MCP tools/list → 收到 4 个工具定义
客户端发送 MCP tools/call(legal_query, {question: "..."}) → 收到 AI 回答
```

**Step 4: 查询审核结果**
```
客户端发送 MCP tools/call(get_consultation, {consultation_id: "..."}) → 状态
```

---

## 5. 注意事项

### 5.1 Token 过期

JWT Token 过期后 SSE 连接会断开，客户端需要：
1. 通过 `POST /api/v1/auth/refresh` 刷新 Token
2. 使用新 Token 重新建立 SSE 连接

### 5.2 所需基础设施

对端 MCP 服务正常运行需要以下组件：
- **PostgreSQL** — 用户认证、会话管理、咨询单存储
- **Qdrant** — 知识库向量检索
- **Ollama / DeepSeek API** — LLM 生成回答
- **知识库文档** — 已向量化入库的法律法规文档

如果启动时这些组件不可用，对应的工具会返回明确的错误提示。

### 5.3 安全建议

- ✅ 使用 HTTPS 暴露 MCP 端点（防止 Token 在传输中泄露）
- ✅ Token 不要在 URL 中长时间暴露 —— Claude Desktop/Cursor 配置文件中会明文存储
- ✅ 定期轮换 JWT Secret Key
- ✅ 建议为 MCP 调用创建专用低权限用户
