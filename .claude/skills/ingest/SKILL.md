---
name: ingest
description: 知识库文档上传与向量化入库
---

## 知识库文档入库

### 1. 查看入库状态
```bash
cd backend && python -c "
import asyncio
from app.core.database import async_session
from app.models.knowledge import KnowledgeDocument
from sqlalchemy import select
async def run():
    async with async_session() as db:
        result = await db.execute(
            select(KnowledgeDocument).order_by(KnowledgeDocument.created_at.desc()).limit(20)
        )
        for d in result.scalars().all():
            print(f'{d.id} | {d.filename} | 状态={d.status} | 分块={d.chunk_count} | {d.created_at}')
asyncio.run(run())
"
```

### 2. 上传文件并入库
```bash
cd backend && python -c "
import asyncio
from app.rag.ingest import ingest_file
async def run():
    filepath = input('文件路径: ').strip()
    doc_id = input('文档 ID（可选，留空自动生成）: ').strip() or None
    count = await ingest_file(filepath, doc_id=doc_id)
    print(f'入库完成，共 {count} 个分块')
asyncio.run(run())
"
```

### 3. 清空知识库重新入库
```bash
cd backend && python -c "
from qdrant_client import QdrantClient
from app.core.config import get_settings
s = get_settings()
client = QdrantClient(url=s.qdrant_url)
client.delete_collection(s.qdrant_collection)
print(f'集合 {s.qdrant_collection} 已删除')
"
```

### 4. 查看 Qdrant 集合统计
```bash
cd backend && python -c "
from qdrant_client import QdrantClient
from app.core.config import get_settings
s = get_settings()
client = QdrantClient(url=s.qdrant_url)
info = client.get_collection(s.qdrant_collection)
count = client.count(s.qdrant_collection)
print(f'集合: {s.qdrant_collection}')
print(f'向量数: {count.count}')
print(f'维度: {info.config.params.vectors.size}')
"
```
