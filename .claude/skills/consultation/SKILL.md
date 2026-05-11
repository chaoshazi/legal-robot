---
name: consultation
description: 咨询单审核工作流管理
---

## 咨询单审核管理

### 1. 查看待审核咨询单
```bash
cd backend && python -c "
import asyncio
from app.core.database import async_session
from app.models.consultation import Consultation
from sqlalchemy import select
async def run():
    async with async_session() as db:
        result = await db.execute(
            select(Consultation).where(Consultation.status == 'draft').order_by(Consultation.created_at.desc()).limit(10)
        )
        for c in result.scalars().all():
            print(f'{c.id} | {c.status} | {c.question[:50]}... | {c.created_at}')
asyncio.run(run())
"
```

### 2. 查看审核日志
```bash
cd backend && python -c "
import asyncio
from app.core.database import async_session
from app.models.audit_log import AuditLog
from sqlalchemy import select
async def run():
    async with async_session() as db:
        result = await db.execute(
            select(AuditLog).where(AuditLog.resource == 'consultation').order_by(AuditLog.created_at.desc()).limit(10)
        )
        for log in result.scalars().all():
            print(f'{log.id} | {log.action} | {log.user_id} | {log.created_at}')
asyncio.run(run())
"
```

### 3. 查看某咨询单的完整对话
```bash
cd backend && python -c "
import asyncio, uuid
from app.core.database import async_session
from app.models.message import Message
from sqlalchemy import select
async def run():
    consultation_id = input('咨询单 ID: ').strip()
    async with async_session() as db:
        from app.models.consultation import Consultation
        c = await db.get(Consultation, uuid.UUID(consultation_id))
        if not c:
            print('咨询单不存在'); return
        print(f'问题: {c.question}')
        print(f'回答: {c.draft_answer[:200]}...')
        print(f'状态: {c.status}')
        # 对应的会话消息
        result = await db.execute(
            select(Message).where(Message.session_id == c.session_id).order_by(Message.created_at)
        )
        for m in result.scalars().all():
            print(f'[{m.role}] {m.content[:100]}')
asyncio.run(run())
"
```

### 状态流转
- `draft`（AI 草稿）→ `published`（律师发布）或 `rejected`（驳回）
- 律师/管理员角色发布时自动设为 `published`
- 普通用户提问时创建 `draft`
