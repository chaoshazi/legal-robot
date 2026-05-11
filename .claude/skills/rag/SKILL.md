---
name: rag
description: RAG 知识库构建与管理
---

## RAG 系统

### 技术组件
- **向量库**：Qdrant（开源、高性能）
- **嵌入模型**：通过本地 Ollama 接入
  - mxbai-embed-large（默认，334M，质量最好）
  - nomic-embed-text（137M，均衡）
  - all-minilm:l6-v2（23M，轻量）
- **分块策略**：RecursiveCharacterTextSplitter (1000/200)
- **检索方式**：Qdrant 向量检索 + BM25 混合

### 知识库入库流程
```
法律文本(.txt) → 分块 → Ollama 嵌入向量 → 存入 Qdrant
```

### 操作步骤

```bash
# 1. 把法律文档存为 .txt 文件
cp 民法典.txt backend/data/

# 2. 运行入库脚本（会自动嵌入 + 存入 Qdrant）
cd backend && python -m app.rag.ingest
```

### 法律数据源（分批入库）
**第一批**：民法典总则 + 合同编（快速验证管道）
**第二批**：刑法全文、劳动合同法全文、最高法指导案例

### 本地 Ollama
Ollama 已在本地运行，embedding 模型列表：
- `mxbai-embed-large`（默认）
- `nomic-embed-text`
- `all-minilm:l6-v2`

在 `.env` 中配置 `OLLAMA_EMBED_MODEL` 切换模型。

### Agent 工具
- `search_laws` — 检索法律条文
- `search_cases` — 检索指导案例
- `calculate_compensation` — 计算赔偿金额
