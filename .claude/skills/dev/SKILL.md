---
name: dev
description: 启动本地开发环境
---

## 启动开发环境

需要同时启动以下服务：

### 1. 基础设施（Docker）
```bash
docker compose up -d postgres qdrant
```

### 2. 后端（FastAPI）
```bash
cd backend && uvicorn app.main:app --reload --port 8000
```

### 3. 前端（Vite + React）
```bash
cd frontend && npm run dev
```

或者一句启动全部：`bash scripts/make.sh dev`

### 环境要求
- Python 3.12+
- Node.js 18+
- Docker & Docker Compose
- 复制 `.env.example` 为 `.env` 并填写配置

### 技术栈
- 后端：FastAPI + SQLAlchemy(async) + Alembic + Pydantic v2
- 前端：React 18 + TypeScript + Vite + Ant Design + Zustand + React Router v6 + Axios
- AI：LangChain Core + DeepSeek API
- 向量库：Qdrant + BAAI/bge-large-zh-v1.5
- 数据库：PostgreSQL 15+
- 认证：JWT (access_token 8h + refresh_token 30d) + RBAC
- 部署：Docker Compose + Nginx
