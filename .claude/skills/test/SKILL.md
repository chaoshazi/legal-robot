---
name: test
description: 运行后端测试
---

## 运行测试

```bash
cd backend && pytest -v
```

### 测试策略
- 单元测试：pytest + pytest-asyncio（测试 service 层逻辑）
- API 测试：httpx AsyncClient（测试所有 endpoint）
- 数据库测试：使用测试 PostgreSQL（Docker 临时库）
- Agent 测试：模拟 LLM 响应，测试 tool 调用逻辑

### 常用命令
- 运行单个测试文件：`cd backend && pytest tests/test_auth.py -v`
- 带覆盖率运行：`cd backend && pytest --cov=app -v`
- 运行特定测试函数：`cd backend && pytest tests/test_auth.py::test_login -v`
