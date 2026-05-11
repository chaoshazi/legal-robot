---
name: migrate
description: 数据库迁移管理（Alembic）
---

## 数据库迁移

### 应用待处理迁移
```bash
cd backend && alembic upgrade head
```

### 创建新迁移（自动检测模型变更）
```bash
cd backend && alembic revision --autogenerate -m "描述变更内容"
```

### 回滚迁移
```bash
cd backend && alembic downgrade -1
```

### 查看当前版本
```bash
cd backend && alembic current
```

### 数据库模型
- **users** — 用户表（UUID 主键、email、phone、hashed_password、display_name、role_id、is_active）
- **roles** — 角色表（user/lawyer/admin）
- **qa_histories** — 问答记录（question、answer、sources JSONB、tokens_used、model、latency_ms）
- **audit_logs** — 审计日志（action、resource、detail JSONB、ip_address、created_at 索引）
- **refresh_tokens** — 刷新令牌（token_hash、expires_at、revoked）
