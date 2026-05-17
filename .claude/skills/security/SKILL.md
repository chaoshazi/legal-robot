---
name: security
description: 安全规范与合规要求
---

## 安全规范

### 认证与授权 ✅
- JWT 双 Token 机制（access 8h + refresh 30d）
- RBAC 三角色：user（普通）、lawyer（专家）、admin（管理员）
- 密码 bcrypt 哈希存储

### API 安全 ✅
- CORS 生产环境限制为 `CORS_ORIGINS` 配置的域名列表
- 速率限制（slowapi）：认证端点 5-10请求/分钟，全局默认 30请求/分钟
- 请求体大小限制（`MAX_REQUEST_SIZE_MB`），上传端点豁免
- SQLAlchemy ORM 防 SQL 注入
- 敏感词过滤中间件（聊天/认证入口拦截，code 4002）

### 内容安全 ✅
- 输入敏感词过滤中间件（覆盖违法/暴力/诈骗/色情类别）
- 输出强制拼接免责声明
- 审计日志记录所有关键操作

### 合规要求
- 审计日志保留 180 天（服务启动时自动清理，提供独立清理脚本）
- 问答记录包含完整引用来源
- AI 输出附带法条引用

### 部署安全
- HTTPS 强制（生产环境 nginx SSL 配置）
  - HTTP → HTTPS 301 重定向
  - TLSv1.2 + TLSv1.3
  - 证书挂载：`nginx/ssl/fullchain.pem` + `privkey.pem`
  - Let's Encrypt 通过 `/.well-known/acme-challenge/` 自动续签
- 环境变量管理敏感配置（禁止硬编码）
- Docker 容器化隔离
