---
name: api
description: API 设计规范与接口文档
---

## API 设计规范

### 统一响应格式
```json
// 成功
{ "code": 0, "message": "ok", "data": { ... } }

// 失败
{ "code": 4001, "message": "邮箱已被注册", "data": null }
```

### 错误码定义
| code | 含义 |
|---|---|
| 0 | 成功 |
| 1001 | 凭证无效（密码错误） |
| 1002 | Token 过期或无效 |
| 1003 | 权限不足 |
| 2001 | 请求参数校验失败 |
| 2002 | 资源已存在 |
| 2003 | 资源不存在 |
| 3001 | 请求频率限制 |
| 4001 | AI 服务异常 |
| 4002 | 敏感内容拦截 |
| 5000 | 服务器内部错误 |

### 接口列表
- `POST /api/v1/auth/register` — 注册
- `POST /api/v1/auth/login` — 登录
- `POST /api/v1/auth/refresh` — 刷新 Token
- `GET /api/v1/users/me` — 获取个人信息
- `PATCH /api/v1/users/me` — 更新个人信息
- `POST /api/v1/chat/ask` — 发送问题（流式 SSE 返回）
- `GET /api/v1/chat/history` — 历史记录（分页）

### 认证方式
- Header: `Authorization: Bearer <access_token>`
- access_token 有效期 8 小时
- refresh_token 有效期 30 天，服务端可撤销
- 前端 Axios 拦截 401 → 自动刷新 → 重放请求 → 刷新失败跳转登录页
