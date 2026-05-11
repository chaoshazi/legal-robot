# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## 项目概述

生产级法律咨询机器人系统。AI 生成回答 → 律师审核 → 用户可见。

## 常用命令

### 开发
```bash
# 启动基础设施（PostgreSQL + Qdrant）
docker compose up -d postgres qdrant

# 启动后端（热重载）
cd backend && uvicorn app.main:app --reload --port 8000

# 启动前端
cd frontend && npm run dev
```

### 测试
```bash
cd backend && pytest -v
cd backend && pytest tests/test_auth.py -v    # 单个文件
```

### 数据库
```bash
cd backend && alembic upgrade head              # 应用迁移
cd backend && alembic revision --autogenerate -m "desc"  # 创建迁移
cd backend && python scripts/seed.py            # 初始化种子数据
```

## 项目结构

```
frontend/          React 18 + TypeScript + Ant Design + Zustand
backend/           FastAPI + SQLAlchemy(async) + LangChain
├── api/v1/        路由层
├── core/          配置/JWT/DB
├── models/        ORM 模型
├── schemas/       Pydantic 请求/响应
├── services/      业务逻辑
├── agent/         LangChain Agent + 语义缓存
└── rag/           混合检索 + 知识库入库
```

## 核心规范

- API 响应格式：`{code: number, message: string, data: T | null}`
- 认证方式：`Authorization: Bearer <access_token>`
- Error code: 0=成功, 1001=凭证无效, 1002=Token过期, 1003=权限不足, 2001=参数错误, 4001=AI异常
- 禁止硬编码：所有配置通过环境变量读取
- Fail Fast：参数/权限/资源校验在入口完成
- 多轮对话：sessions → messages 结构
- 审核工作流：AI草稿 → lawyer审核 → 用户可见

## 数据库模型

- users / roles / refresh_tokens — 认证与权限
- sessions / messages — 多轮对话
- consultations — 咨询单与审核
- qa_histories — 问答日志
- audit_logs — 审计日志（保留180天）
