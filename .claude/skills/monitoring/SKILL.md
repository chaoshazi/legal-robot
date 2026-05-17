---
name: monitoring
description: 监控与可观测性配置
---

## 监控体系

### LangFuse（Agent 追踪）
- 自动追踪 Agent 执行链（标准+流式）
- 记录 Token 消耗和延迟
- 评分与评估集成
- 配置：设置 `LANGFUSE_SECRET_KEY` 环境变量

### Prometheus + Grafana（指标监控）
- 自定义指标：
  - `legal_bot_requests_total` — 总请求数
  - `legal_bot_errors_total` — 错误数
  - `legal_bot_tool_calls_total` — 工具调用数
- Grafana 可视化面板

### Sentry（错误追踪）
- 前端 + 后端双端接入
- FastAPI 集成（sentry-sdk）
- React 集成

### 审计日志
- 记录每个问答的用户、时间、模型、耗时
- JSON 格式，可接入 ELK/Loki
- 180 天保留策略
