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

### 认证方式
- Header: `Authorization: Bearer <access_token>`
- access_token 有效期 8 小时
- refresh_token 有效期 30 天，服务端可撤销
- 前端 Axios 拦截 401 → 自动刷新 → 重放请求 → 刷新失败跳转登录页

## 接口列表

### 认证 `/auth`
| 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|
| POST | `/api/v1/auth/register` | 注册 | 公开 |
| POST | `/api/v1/auth/login` | 登录（email/password） | 公开 |
| POST | `/api/v1/auth/refresh` | 刷新 Token | 公开（需 refresh_token） |
| POST | `/api/v1/auth/me/password` | 修改密码 | 登录用户 |

### 用户 `/users`
| 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|
| GET | `/api/v1/users/me` | 获取个人信息 | 登录用户 |
| PATCH | `/api/v1/users/me` | 更新个人信息 | 登录用户 |
| GET | `/api/v1/users` | 用户列表 | admin |
| POST | `/api/v1/users` | 创建用户 | admin |
| PUT | `/api/v1/users/{user_id}` | 更新用户（角色/状态） | admin |
| DELETE | `/api/v1/users/{user_id}` | 删除用户 | admin |
| PUT | `/api/v1/users/{user_id}/password` | 重置密码 | admin |
| GET | `/api/v1/users/roles` | 角色列表 | admin |
| POST | `/api/v1/users/roles` | 创建角色 | admin |
| PUT | `/api/v1/users/roles/{role_id}` | 更新角色 | admin |
| DELETE | `/api/v1/users/roles/{role_id}` | 删除角色 | admin |

### 聊天 `/chat`
| 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|
| POST | `/api/v1/chat/sessions` | 创建会话 | 登录用户 |
| PUT | `/api/v1/chat/sessions/{session_id}` | 重命名会话 | 登录用户 |
| GET | `/api/v1/chat/sessions` | 会话列表 | 登录用户 |
| GET | `/api/v1/chat/sessions/{session_id}/messages` | 消息列表 | 登录用户 |
| DELETE | `/api/v1/chat/sessions/{session_id}` | 删除会话 | 登录用户 |
| POST | `/api/v1/chat/ask` | 发送提问（非流式） | 登录用户 |
| POST | `/api/v1/chat/stream` | 发送提问（流式 SSE） | 登录用户 |
| POST | `/api/v1/chat/upload` | 上传附件（图片/音频/文档） | 登录用户 |
| POST | `/api/v1/chat/transcribe/{attachment_id}` | 音频转文字 | 登录用户 |
| GET | `/api/v1/chat/download/{attachment_id}` | 下载附件 | 登录用户 |

### 咨询单 `/consultations`
| 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|
| GET | `/api/v1/consultations` | 咨询单列表 | 用户看自己的，律师/admin 看全部 |
| GET | `/api/v1/consultations/pending` | 待审核列表 | lawyer/admin |
| POST | `/api/v1/consultations/{consultation_id}/review` | 审核（发布/驳回），可记录评分 | lawyer/admin |

### 知识库 `/knowledge`
| 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|
| POST | `/api/v1/knowledge/upload` | 上传文档 | admin |
| GET | `/api/v1/knowledge/documents` | 文档列表 | admin/lawyer |
| POST | `/api/v1/knowledge/ingest/{doc_id}` | 向量化入库 | admin |
| DELETE | `/api/v1/knowledge/documents/{doc_id}` | 删除文档 | admin |

### 工具 `/tools`
| 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|
| GET | `/api/v1/tools` | 工具列表（DB + builtin） | admin/lawyer |
| POST | `/api/v1/tools` | 创建自定义工具 | admin |
| PUT | `/api/v1/tools/{tool_id}` | 更新工具 | admin |
| DELETE | `/api/v1/tools/{tool_id}` | 删除工具 | admin |

### MCP 服务器 `/mcp`
| 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|
| GET | `/api/v1/mcp/servers` | 服务器列表 | admin/lawyer |
| POST | `/api/v1/mcp/servers` | 创建服务器 | admin |
| PUT | `/api/v1/mcp/servers/{server_id}` | 更新服务器 | admin |
| DELETE | `/api/v1/mcp/servers/{server_id}` | 删除服务器 | admin |
| POST | `/api/v1/mcp/servers/{server_id}/test` | 测试连接 | admin |
| POST | `/api/v1/mcp/servers/{server_id}/reconnect` | 重连并刷新工具 | admin |
| GET | `/api/v1/mcp/servers/{server_id}/tools` | 工具列表 | admin/lawyer |
| POST | `/api/v1/mcp/servers/{server_id}/toggle` | 启用/禁用 | admin |

### 系统设置 `/settings`
| 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|
| GET | `/api/v1/settings/ollama-models` | Ollama 对话模型列表 | admin/lawyer |
| GET | `/api/v1/settings/ollama-embed-models` | Ollama 嵌入模型列表 | admin/lawyer |
| GET | `/api/v1/settings/llm` | 获取 LLM 配置 | admin/lawyer |
| PUT | `/api/v1/settings/llm` | 更新 LLM 配置 | admin |
| POST | `/api/v1/settings/llm/test` | 测试 LLM 连通性 | admin |
| GET | `/api/v1/settings/agent` | 获取 Agent 配置 | admin/lawyer |
| PUT | `/api/v1/settings/agent` | 更新 Agent 配置 | admin |
| GET | `/api/v1/settings/unified` | 获取合并配置 | admin/lawyer |
| PUT | `/api/v1/settings/unified` | 更新合并配置 | admin |

### 权限 `/permissions`
| 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|
| GET | `/api/v1/permissions/roles` | 角色菜单权限列表 | admin/lawyer |
| PUT | `/api/v1/permissions/roles/{role_id}` | 更新角色菜单权限 | admin |

### 审计日志 `/audit-logs`
| 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|
| GET | `/api/v1/audit-logs` | 审计日志列表（分页+过滤） | admin |
| GET | `/api/v1/audit-logs/actions` | action 枚举值列表 | admin |

### 评估 `/evaluations`
| 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|
| GET | `/api/v1/evaluations` | 评估列表（分页+过滤） | admin/lawyer |
| GET | `/api/v1/evaluations/score-names` | score_name 枚举值列表 | admin/lawyer |

### 外部 MCP `/external-mcp`
| 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|
| GET | `/api/v1/external-mcp/sse` | SSE 传输入口（Cursor 等客户端） | 公开 |
| POST | `/api/v1/external-mcp/messages/` | MCP 协议消息端点 | 公开 |
