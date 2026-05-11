---
name: security
description: 安全规范与合规要求
---

## 安全规范

### 认证与授权
- JWT 双 Token 机制（access 8h + refresh 30d）
- RBAC 三角色：user（普通）、lawyer（专家）、admin（管理员）
- 密码 bcrypt 哈希存储

### API 安全
- CORS 只允许前端域名
- 速率限制防止滥用（slowapi）
- 请求体大小限制
- SQLAlchemy ORM 防 SQL 注入

### 内容安全
- 输入敏感词过滤中间件
- 输出强制拼接免责声明
- 审计日志记录所有关键操作

### 合规要求
- 审计日志保留 180 天
- 问答记录包含完整引用来源
- AI 输出附带法条引用

### 部署安全
- HTTPS 强制
- 环境变量管理敏感配置（禁止硬编码）
- Docker 容器化隔离
