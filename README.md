# Legal Consult Bot

> **生产级 AI 法律咨询机器人** — 融合 Agent + RAG + MCP + 人工审核工作流 + 全链路可观测性。

AI 生成回答初稿 → 律师审核发布 → 用户可见。覆盖从知识库构建、Agent 编排、LLM 可观测性到生产化部署的完整 AI 应用链路。

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (React 18)                      │
│  Ant Design UI  │  Zustand State  │  RBAC Menu  │  SSE Stream   │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP / SSE
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Nginx Reverse Proxy                          │
│        SSE buffering off · read timeout 300s · CORS             │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                   FastAPI Backend (Async)                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────────┐  │
│  │ Auth/RBAC│  │  Chat    │  │Consult   │  │ Knowledge     │  │
│  │ JWT轮换  │  │ SSE流式  │  │审核工作流│  │ 文档管理      │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬────────┘  │
│       │              │             │               │           │
│  ┌────▼──────────────▼─────────────▼───────────────▼────────┐  │
│  │              LangGraph Agent (create_agent)               │  │
│  │  ChatOpenAI(DS/llama) · ChatOllama · BaseLanguageModel   │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐              │  │
│  │  │ToolRegist│  │Semantic  │  │  MCP     │              │  │
│  │  │ ry(聚合) │  │ Cache    │  │ Client   │              │  │
│  │  │@tool→Base│  └──────────┘  │Structured│              │  │
│  │  │Tool      │               │Tool      │              │  │
│  │  └────┬─────┘               └────┬─────┘              │  │
│  └───────┼───────────────────────────┼─────────────────────┘  │
│          │                           │                         │
│  ┌───────▼───────────────────────────▼─────────────────────┐  │
│  │  Hybrid RAG (Qdrant + LangChain)    MCP Servers          │  │
│  │  QdrantVectorStore · Document       自定义工具注册        │  │
│  │  RecursiveCharacterTextSplitter     StructuredTool        │  │
│  └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                           │
         ┌─────────────────┼──────────────────┐
         ▼                 ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────────┐
│  PostgreSQL  │  │    LLM       │  │   External API   │
│  15 / 14表   │  │ DeepSeek     │  │   Web Search     │
│              │  │ Ollama       │  │   Tavily / DDG   │
│              │  │ llama.cpp    │  │                  │
└──────────────┘  └──────────────┘  └──────────────────┘

                     Observability Stack
┌─────────────────────────────────────────────────────────────────┐
│  LangFuse(LLM Trace) · Prometheus(Metrics) · Grafana(Dashboards)│
│  Loki(Logs) · Sentry(Errors) · Audit Logs(180天保留)            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 核心能力

### AI Agent 引擎

基于 `langchain.agents.create_agent` 构建的 LangGraph `CompiledStateGraph` 状态图，通过 `recursion_limit=25` 控制工具调用深度。

**LLM 抽象层**：DeepSeek / llama.cpp 通过 `langchain_openai.ChatOpenAI`，Ollama 通过 `langchain_ollama.ChatOllama`，经由 `BaseLanguageModel` 接口统一，`_build_llm()` 工厂按 provider 切换。

**DeepSeek 深度定制**：自定义 `_DeepSeekChatOpenAI` 继承 `ChatOpenAI`，重写 `_convert_chunk_to_generation_chunk` 钩子捕获 `reasoning_content`，实现推理链路前端渲染——这是深入 LangChain 源码层的定制。

**工具系统**：通过统一 `ToolRegistry` 聚合三类来源：

| 工具来源 | 数量 | LangChain 抽象 | 示例 |
|---------|------|---------------|------|
| 内置工具 | 6 个 | `@tool` 装饰器 → `BaseTool` | 知识库检索、联网搜索、法律赔偿计算、Python沙箱执行、数学计算、日期时间 |
| 自定义工具 | 动态 | `StructuredTool.from_function()` | 通过管理后台注册的自定义函数 |
| MCP 工具 | 动态 | MCP json-schema → `StructuredTool` | 外部服务工具 |

支持运行时动态修改系统提示词和激活的工具列表。

`[create_agent]` `[LangGraph]` `[_DeepSeekChatOpenAI]` `[@tool]` `[ToolRegistry]` `[BaseLanguageModel]`

### 混合检索 RAG

- **向量检索**：`QdrantVectorStore.asimilarity_search()` 密集向量检索（k=8），结果以 `Document` 对象承载
- **关键词匹配**：法条编号精确匹配，中文数字→阿拉伯数字自动转换
- **文本分块**：`RecursiveCharacterTextSplitter(chunk_size=400, chunk_overlap=50)` 智能递归分块
- **嵌入模型**：`OllamaEmbeddings` + `@lru_cache(maxsize=256)` 层（3 个模型：mxbai-embed-large / nomic-embed-text / all-minilm）
- **多格式文档入库**：支持 PDF（含 OCR 扫描件）、DOCX、XLSX、TXT、MD

`[QdrantVectorStore]` `[RecursiveCharacterTextSplitter]` `[Document]` `[Hybrid Retrieval]` `[OCR]`

### MCP 协议集成

内置 **MCP Client Manager**，同时管理多个 MCP Server 连接：
- **stdio 传输**：本地子进程通信
- **SSE 传输**：远程 HTTP 服务
- **工具自动发现**：MCP 工具的 JSON Schema `inputSchema` → Pydantic 模型自动转换，包装为 `StructuredTool(name, description, args_schema, coroutine)` 注册到 `ToolRegistry`
- **自身暴露为 MCP Server**：支持 Cursor、Claude Desktop 等 MCP Client 反向连接

`[MCP]` `[StructuredTool]` `[ToolRegistry]` `[MCP Client]` `[MCP Server]`

### 审核工作流

```
用户提问 → AI 生成草稿 → 律师审核 → [发布] → 用户可见
                                  → [拒绝 + 评分] → 退回重审
```

- 多维度评分体系（通过 LangFuse 持久化）
- LangFuse Trace 全链路追踪（含模型、Token 消耗、延迟）
- 完整的会话→消息→咨询单关联

`[Review Workflow]` `[Human-in-the-Loop]` `[LangFuse Evaluation]`

### 全链路可观测性

| 维度 | 工具 | 覆盖范围 |
|------|------|---------|
| LLM 追踪 | **LangFuse** | Agent 调用链路、Token 消耗、评分回传 |
| 指标监控 | **Prometheus** | QPS、延迟、错误率 |
| 可视化 | **Grafana** | Prometheus + Loki 数据源预配置 |
| 日志聚合 | **Loki + Promtail** | Docker 容器日志、应用日志、Nginx 日志 |
| 错误追踪 | **Sentry** | FastAPI 集成，自动捕获异常 |
| 操作审计 | **audit_logs 表** | 所有管理操作记录，180 天保留 |

`[Observability]` `[Grafana]` `[Sentry]` `[Loki]`

### RBAC 权限体系

三角色模型 + 菜单级权限控制：

| 角色 | 权限 | 典型操作 |
|------|------|---------|
| 管理员 | 全部权限 | 用户管理、系统配置、MCP 管理、角色分配 |
| 律师 | 业务操作 | 审核咨询单、管理知识库、查看评分 |
| 普通用户 | 基础操作 | 提问、查看会话、修改个人资料 |

前端路由由 `RoleGuard` 保护，后端通过 `require_role()` 依赖注入校验，菜单可见性由 `role_menus` 表控制。

`[RBAC]` `[Role-based Access]` `[Audit Trail]`

### 流式对话与推理展示

- **SSE Streaming**：`agent.astream(inputs, stream_mode="messages")` 逐 token 产出，按 `langgraph_node` 元数据路由
- **工具调用流式块**：监听 `chunk.tool_call_chunks` 实时渲染 Agent 工具调用状态
- **DeepSeek 推理展示**：自定义 `_DeepSeekChatOpenAI` 继承 `ChatOpenAI`，重写 `_convert_chunk_to_generation_chunk` 钩子捕获 `delta.reasoning_content`，前端独立渲染思考链路
- **LLM Provider 热切换**：通过 `BaseLanguageModel` 接口统一，运行时可切换 DeepSeek / Ollama / llama.cpp
- **联网搜索开关**：用户可控制是否启用 Web Search

`[agent.astream]` `[stream_mode=messages]` `[tool_call_chunks]` `[SSE]` `[_DeepSeekChatOpenAI]`

### 前端配置中心

管理员可在运行态动态调整（无需重启后端）：
- **LLM 配置**：Provider 切换、模型名、API Key、API Base
- **Agent 配置**：系统提示词、激活工具列表、知识库开关、MCP 开关
- **Ollama 模型探测**：自动列出可用模型和嵌入模型

`[Runtime Config]` `[Dynamic Switching]`

---

## LangChain 深度集成

项目基于 LangChain 0.3 生态构建，使用了 8 个子包、覆盖 10+ 文件，从 Agent 编排到向量检索贯穿全链路：

| LangChain 包 | 核心类/函数 | 使用场景 |
|-------------|------------|---------|
| `langchain.agents` | `create_agent` | LangGraph Agent 工厂，工具调用循环状态图 |
| `langchain_openai` | `ChatOpenAI` | DeepSeek / llama.cpp LLM Provider（自定义子类 `_DeepSeekChatOpenAI`） |
| `langchain_ollama` | `ChatOllama` | Ollama 本地 LLM Provider |
| `langchain_core.tools` | `@tool`, `BaseTool`, `StructuredTool` | 内置工具定义、自定义与 MCP 工具动态包装 |
| `langchain_core.messages` | `HumanMessage`, `AIMessage`, `SystemMessage`, `ToolMessage` | 对话历史重建、Agent 输入协议、结果提取 |
| `langchain_qdrant` | `QdrantVectorStore` | 向量存储与语义检索 |
| `langchain_text_splitters` | `RecursiveCharacterTextSplitter` | 文档智能递归分块 |
| `langchain_community.embeddings` | `OllamaEmbeddings` | 本地嵌入模型 + LRU 缓存 |
| `langchain_core.documents` | `Document` | 检索结果元数据承载 |
| `langchain_core.language_models` | `BaseLanguageModel` | 多 Provider 统一 LLM 接口 |

---

## Tech Stack

| 层级 | 技术 | 选型理由 |
|------|------|---------|
| **Frontend** | React 18 + TypeScript + Ant Design 5 + Zustand 5 | SPA 架构、类型安全、企业级组件库、轻量状态管理 |
| **Backend** | FastAPI + SQLAlchemy 2.0 (async) + Pydantic v2 | 异步高性能、类型化 ORM、声明式验证 |
| **AI Agent** | LangChain 0.3（8 子包）+ LangGraph + MCP SDK 1.0 | Agent 工厂、LLM 抽象、工具系统、消息协议、RAG 集成 |
| **Vector Store** | Qdrant 1.13 + Ollama Embeddings | 高性能向量检索、本地化嵌入、多模型 |
| **Database** | PostgreSQL 15 + Alembic | 成熟稳定、异步驱动、版本化迁移 |
| **LLM Providers** | DeepSeek API + Ollama + llama.cpp | 云+本地双模式、运行时可切换 |
| **Monitoring** | Prometheus + Grafana + Loki + Sentry | 指标+日志+错误三位一体 |
| **LLM Observability** | LangFuse v2 | Trace + Evaluation 全链路追踪 |
| **Infrastructure** | Docker Compose + Nginx | 环境一致性、反向代理、SSE 优化 |
| **Security** | JWT (HS256) + bcrypt + RBAC + Audit Log | 令牌轮换、密码哈希、角色控制、操作审计 |

---

## Project Structure

```
backend/
├── api/v1/                 # 路由层 — 12 个路由模块
│   ├── auth.py             # 登录/注册/令牌刷新
│   ├── chat.py             # 会话管理 + SSE 流式对话
│   ├── consultations.py    # 咨询单审核工作流
│   ├── knowledge.py        # 知识库文档管理
│   └── mcp.py              # MCP Server CRUD
├── agent/                  # AI Agent 核心
│   ├── agent.py            # LangGraph Agent 工厂
│   ├── tools.py            # 6 个内置工具
│   ├── registry.py         # 统一工具注册表
│   ├── mcp_client.py       # MCP Client 管理器
│   ├── cache.py            # 语义缓存（嵌入相似度）
│   └── sandbox.py          # Python 沙箱执行器
├── rag/                    # RAG 流水线
│   ├── embeddings.py       # 嵌入模型（LRU 缓存）
│   ├── ingest.py           # 多格式文档入库
│   └── retriever.py        # 混合检索（向量+关键词）
├── models/                 # SQLAlchemy ORM — 14 个表
├── schemas/                # Pydantic 请求/响应模型
├── services/               # 业务逻辑（审计、评分）
├── core/                   # 基础设施（配置/JWT/DB/LangFuse）
├── middleware/              # 中间件（免责声明、敏感词过滤）
├── mcp_servers/             # 内置 MCP Server
├── alembic/                 # 数据库迁移（7 个版本）
└── tests/                  # 测试
frontend/
├── src/pages/              # 13 个页面
├── src/api/                # API 调用层（10 个模块）
├── src/stores/             # Zustand 状态管理
├── src/router/             # 路由 + ProtectedRoute + RoleGuard
└── src/types/              # TypeScript 类型定义
```

---

## Quick Start

### 一键启动（完整环境）

```bash
docker compose up --build -d
```

包含全部 10 个服务：PostgreSQL + Qdrant + Backend + Prometheus + Grafana + Loki + Promtail + Nginx + LangFuse。

### 分步启动（适合开发调试）

```bash
# 1. 启动基础设施
docker compose up -d postgres qdrant

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 填入 API Key（DeepSeek / Tavily / Sentry 等）

# 3. 应用数据库迁移
cd backend && alembic upgrade head

# 4. 初始化种子数据（角色 + 管理员账号）
cd backend && python scripts/seed.py

# 5. 启动后端（热重载, http://localhost:8888）
cd backend && uvicorn app.main:app --reload --port 8888

# 6. 启动前端（新终端, http://localhost:5173）
cd frontend && npm install && npm run dev
```

### 默认账号

| 角色 | Email | 密码 |
|------|-------|------|
| 管理员 | admin@legalbot.com | `admin123456`（通过 `ADMIN_PASSWORD` 覆盖） |

### 常用命令

```bash
make test        # 运行后端测试
make seed        # 初始化种子数据
make lint        # 代码检查（ruff + eslint）
make migration msg="description"  # 生成数据库迁移
```

---

## Screenshots

| | |
|---|---|
| ![Login](screenshots/login.png) | ![Chat](screenshots/chat.png) |
| **登录注册** | **AI 对话** — 流式输出 + 工具调用 + 推理展示 |
| ![Consultations](screenshots/consultations.png) | ![Knowledge Base](screenshots/knowledge.png) |
| **咨询单审核** — AI草稿 → 律师审核 | **知识库管理** — 文档上传与入库 |
| ![MCP Servers](screenshots/mcp.png) | ![Models](screenshots/models.png) |
| **MCP 服务器** — 前沿协议集成 | **LLM 配置** — 多 Provider 切换 |
| ![Settings](screenshots/settings.png) | ![Tools](screenshots/tools.png) |
| **Agent 参数** — 运行时动态配置 | **工具管理** — 内置+自定义+MCP |
| ![Users](screenshots/users.png) | ![Permissions](screenshots/permissions.png) |
| **用户管理** — RBAC 权限控制 | **菜单权限** — 基于角色 |
| ![Profile](screenshots/profile.png) | ![Skills](screenshots/skills.png) |
| **个人中心** — 资料编辑 | **技能管理** |

---

## 生产化特性

| 特性 | 实现 |
|------|------|
| 健康检查 | FastAPI `/health` 端点 + Docker Compose 健康检测 |
| 优雅关闭 | Uvicorn 优雅退出 + 连接池清理 |
| 错误追踪 | Sentry SDK 自动捕获 |
| 指标监控 | Prometheus FastAPI Instrumentator（QPS/延迟/错误率） |
| 日志聚合 | Lokistack3（Docker 日志 + 应用日志 + Nginx 日志）|
| Grafana 大盘 | Prometheus + Loki 数据源预配置 |
| 安全审计 | 所有管理操作写入 audit_logs（180 天保留）|
| 令牌安全 | JWT 访问令牌（8h）+ 刷新令牌轮换（30d），bcrypt 存储 |
| 输入校验 | Pydantic v2 全接口校验 |
| CORS | 生产环境严格配置 |
| 沙箱隔离 | Python 代码执行：子进程 + 静态分析 + 30s 超时 |
| 敏感词过滤 | 中间件层拦截 |
| 免责声明 | 中间件强制展示 |
| Docker 构建 | 多阶段构建、环境分离（开发/生产） |

---

## API 概览

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/auth/login` | 用户登录，返回 JWT |
| `POST` | `/api/v1/auth/register` | 用户注册 |
| `POST` | `/api/v1/chat/stream` | SSE 流式对话 |
| `POST` | `/api/v1/chat/ask` | 非流式对话 |
| `GET` | `/api/v1/consultations/pending` | 待审核咨询单 |
| `POST` | `/api/v1/consultations/{id}/review` | 审核发布/拒绝 |
| `GET` | `/api/v1/knowledge/documents` | 文档列表 |
| `POST` | `/api/v1/knowledge/ingest/{id}` | 文档入库 |
| `POST` | `/api/v1/mcp/servers` | 注册 MCP 服务器 |
| `PUT` | `/api/v1/settings/llm` | 更新 LLM 配置 |
| `GET` | `/api/v1/evaluations` | 评分查询 |
| `GET` | `/api/v1/audit-logs` | 审计日志查询 |

---

## 环境变量

| 变量 | 说明 |
|------|------|
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 |
| `JWT_SECRET_KEY` | JWT 签名密钥（生产环境必改）|
| `POSTGRES_PASSWORD` | 数据库密码（生产环境必改）|
| `QDRANT_HOST` | Qdrant 向量库地址 |
| `OLLAMA_BASE_URL` | Ollama 服务地址 |
| `LANGFUSE_PUBLIC_KEY` | LangFuse 公钥 |
| `LANGFUSE_SECRET_KEY` | LangFuse 密钥 |
| `TAVILY_API_KEY` | Tavily 搜索 API |
| `SENTRY_DSN` | Sentry DSN |
| `ADMIN_PASSWORD` | 管理员初始密码 |

---

## 关于项目

本项目的设计目标是打造一个 **真正可上线的 AI 法律咨询系统**，而非简单的 Demo。

在技术层面的核心思考：
- **Agent 而非 Chain**：法律咨询需要多步推理和工具调用，LangGraph 优于 Chain 模式
- **LangChain 作为 AI 中间件层**：利用 `langchain_core` 的抽象接口（BaseLanguageModel、BaseTool、Embeddings）实现 Provider 无关的 Agent 系统；通过 `create_agent` 获得 LangGraph 状态图而不需要直接编写图逻辑；借助 `QdrantVectorStore` 等集成包降低向量数据库接入成本。LangChain 的核心价值在于**抽象层 + 集成生态**，而非特定实现
- **人工审核关卡**：纯 AI 输出在法律场景不可接受，Human-in-the-Loop 是必须的
- **MCP 作为扩展接口**：MCP 是模型上下文协议的工业标准
- **可观测性是刚需**：没有 LangFuse 和 Prometheus，AI 应用就是黑盒
- **运行时可配置**：AI 领域变化快，固定配置不可维护

后续规划方向：
- 多轮对话的长上下文管理
- 基于用户反馈的在线学习
- 更丰富的 MCP Server 生态

---

## License

MIT
