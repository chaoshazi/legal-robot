---
name: chat-debug
description: 调试聊天 Agent 和知识库检索
---

## 聊天 Agent 调试

### 1. 查看当前 Agent 配置
```bash
cd backend && python -c "
from app.agent.config import get_agent_config
cfg = get_agent_config()
print('active_knowledge_ids:', cfg.get('active_knowledge_ids'))
print('active_tool_ids:', cfg.get('active_tool_ids'))
print('system_prompt:', (cfg.get('system_prompt') or '')[:100])
"
```

### 2. 重置配置缓存（使下次读取从 DB 重新加载）
```bash
cd backend && python -c "
from app.agent.config import reset_agent_config, reset_llm_config
reset_agent_config()
reset_llm_config()
print('config cache reset')
"
```

### 3. 测试知识库检索
```bash
cd backend && python -c "
import asyncio
from app.rag.retriever import async_get_retriever
async def test():
    r = await async_get_retriever()
    docs = await r.ainvoke('工伤赔偿标准')
    print(f'检索到 {len(docs)} 条结果')
    for d in docs[:3]:
        print(f'  - {d.page_content[:100]}...')
    # 测试按 doc_id 过滤
    docs2 = await r.ainvoke('工伤赔偿标准', doc_ids=[])
    print(f'空过滤检索到 {len(docs2)} 条结果（应为 0）')
asyncio.run(test())
"
```

### 4. 测试 LLM 连通性
```bash
cd backend && python -c "
from app.core.config import get_settings
s = get_settings()
print(f'Provider: {s.llm_provider}')
print(f'Model: {s.ollama_model or s.deepseek_model}')
"
```
