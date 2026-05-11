"""External MCP SSE server — exposes the legal consult bot as MCP tools.

External clients (Cursor, Claude Desktop, Dify) connect via SSE transport
and get access to legal-query, knowledge-search, and consultation tools.

Access control is handled at the network level (firewall / VPN / IP whitelist).
There is no built-in token authentication.

Usage — mounted by ``app.api.v1.external_mcp`` into the FastAPI app.
For standalone testing:
    python -c "from app.mcp_servers.external_api_server import mcp; mcp.run(transport='stdio')"
"""

import json
import uuid

from mcp.server.fastmcp import FastMCP

# Default user ID used when the caller does not provide one.
# This is needed because the system creates DB records (sessions, messages,
# consultations) that must be associated with a user.
_DEFAULT_USER_ID = uuid.uuid4()


def _resolve_user_id(user_id: str | None = None) -> uuid.UUID:
    if user_id:
        try:
            return uuid.UUID(user_id)
        except ValueError:
            return _DEFAULT_USER_ID
    return _DEFAULT_USER_ID


# ── FastMCP server ───────────────────────────────────────────────────────────

mcp = FastMCP(
    name="legal-consult-external-api",
    instructions="""法律咨询系统对外 MCP 服务。

提供以下能力：
1. legal_query — 向法律咨询 AI 提问（自动检索知识库 + AI 生成回答）
2. search_knowledge — 检索法律知识库中的相关法规条文
3. get_consultation — 查询咨询单状态与详情
4. list_knowledge_documents — 列出知识库文档""",
)


# ── Tools ────────────────────────────────────────────────────────────────────


@mcp.tool()
async def legal_query(question: str, session_id: str | None = None, user_id: str | None = None) -> str:
    """向法律咨询 AI 提问并获取专业回答。

    该工具会检索知识库中的法律法规，并使用 AI 基于检索结果生成专业回答。
    适用于法律咨询场景：劳动合同纠纷、婚姻财产分割、民间借贷、交通事故等。
    每次调用会自动创建咨询单草稿，待律师审核后发布。

    Args:
        question: 用户的法律咨询问题，应清晰描述事实情况（如"上班途中发生交通事故算工伤吗？"）。
        session_id: 可选会话 ID，传入后保持同一会话的对话上下文连续性。
        user_id: 可选用户标识（如邮箱或 UUID），用于区分不同调用者。不传则使用默认用户。
    """
    from app.core.database import async_session
    from app.models.session import Session as SessionModel
    from app.models.message import Message
    from app.models.consultation import Consultation
    from app.agent.agent import build_agent, DEFAULT_SYSTEM_PROMPT
    from app.agent.config import get_agent_config
    from app.agent.registry import get_registry
    from app.middleware.disclaimer import add_disclaimer
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
    from sqlalchemy import select

    uid = _resolve_user_id(user_id)
    cfg = get_agent_config()
    knowledge_enabled = bool(cfg.get("active_knowledge_ids"))
    registry = get_registry()
    tools = registry.get_agent_tools(
        active_tool_ids=cfg.get("active_tool_ids"),
        active_mcp_ids=cfg.get("active_mcp_ids"),
        knowledge_enabled=knowledge_enabled,
    )
    system_prompt = cfg.get("system_prompt", "") or DEFAULT_SYSTEM_PROMPT
    agent = build_agent(tools, system_prompt)

    # ── Resolve or create session ───────────────────────────────────────
    async with async_session() as db:
        if session_id:
            result = await db.execute(
                select(SessionModel).where(
                    SessionModel.id == session_id,
                    SessionModel.user_id == uid,
                )
            )
            session = result.scalar_one_or_none()
            if session is None:
                session_id = None  # invalid session — create a new one

        if not session_id:
            session = SessionModel(
                id=uuid.uuid4(),
                user_id=uid,
                title=question[:100],
            )
            db.add(session)
            await db.commit()
            await db.refresh(session)

        sid = session.id

        # Save user message
        db.add(Message(id=uuid.uuid4(), session_id=sid, role="user", content=question))
        await db.commit()

    # ── Load history ────────────────────────────────────────────────────
    async with async_session() as db:
        result = await db.execute(
            select(Message)
            .where(Message.session_id == sid)
            .order_by(Message.created_at)
        )
        all_messages = result.scalars().all()

    history = []
    for msg in all_messages[:-1]:  # exclude the current user message
        if msg.role == "user":
            history.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            history.append(AIMessage(content=msg.content))

    # ── Pre-retrieve knowledge ──────────────────────────────────────────
    kb_context: str | None = None
    if knowledge_enabled:
        try:
            from app.rag.retriever import async_get_retriever

            retriever = await async_get_retriever()
            docs = await retriever.ainvoke(
                question, doc_ids=cfg.get("active_knowledge_ids")
            )
            if docs:
                parts = []
                for i, d in enumerate(docs, 1):
                    source = d.metadata.get("source", "法律知识库")
                    parts.append(f"[{i}] 来自《{source}》\n{d.page_content}")
                kb_context = "\n\n".join(parts)
        except Exception:
            import logging

            logging.getLogger("external_mcp").exception(
                "Knowledge retrieval failed in legal_query"
            )

    # ── Build messages and invoke agent ─────────────────────────────────
    messages: list = [*history]
    if kb_context:
        messages.append(
            SystemMessage(
                content="以下是知识库中检索到的相关法律条文，请基于这些内容回答用户问题：\n\n"
                + kb_context
            )
        )
    elif knowledge_enabled:
        messages.append(
            SystemMessage(
                content="知识库检索结果为空，未找到与用户问题相关的法律条文。"
            )
        )
    messages.append(HumanMessage(content=question))

    try:
        result = await agent.ainvoke({"messages": messages})
        answer = ""
        for m in reversed(result.get("messages", [])):
            if isinstance(m, AIMessage) and m.content:
                answer = m.content
                break
        if not answer:
            answer = "抱歉，AI 暂时无法生成回答，请稍后重试。"
    except Exception as e:
        import logging

        logging.getLogger("external_mcp").exception("Agent invoke failed")
        answer = f"AI 服务暂时不可用，请稍后重试。错误：{e}"

    answer = await add_disclaimer(answer)

    # ── Persist assistant message & consultation ────────────────────────
    async with async_session() as db:
        db.add(
            Message(id=uuid.uuid4(), session_id=sid, role="assistant", content=answer)
        )

        consultation = Consultation(
            id=uuid.uuid4(),
            user_id=uid,
            session_id=sid,
            question=question,
            draft_answer=answer,
            status="draft",
        )
        db.add(consultation)
        await db.commit()

    return answer


@mcp.tool()
async def search_knowledge(query: str, top_k: int = 5) -> str:
    """检索法律知识库中的相关文档。

    使用混合检索（向量语义搜索 + 法条编号精确匹配），返回与查询相关的
    法律法规条文原文及出处。

    Args:
        query: 搜索关键词或法律问题描述（如"劳动合同解除经济补偿"）。
        top_k: 返回结果数量（1-20），默认 5。
    """
    top_k = min(max(top_k, 1), 20)
    try:
        from app.rag.retriever import async_get_retriever

        retriever = await async_get_retriever()
        docs = await retriever.ainvoke(query)

        if not docs:
            return json.dumps({"results": [], "total": 0}, ensure_ascii=False)

        results = []
        for d in docs[:top_k]:
            results.append({
                "content": d.page_content,
                "source": d.metadata.get("source", ""),
                "doc_id": str(d.metadata.get("doc_id", "")),
            })

        return json.dumps(
            {"results": results, "total": len(results)}, ensure_ascii=False
        )
    except Exception as e:
        return json.dumps({"error": f"知识库检索失败: {e}"}, ensure_ascii=False)


@mcp.tool()
async def get_consultation(consultation_id: str, user_id: str | None = None) -> str:
    """查询法律咨询单的详细信息和当前审核状态。

    状态说明：
    - draft: AI 已生成草稿，待律师审核
    - published: 律师已审核发布，最终答案对用户可见
    - rejected: 律师已拒绝发布

    Args:
        consultation_id: 咨询单 UUID，从 legal_query 返回的结果中获取。
        user_id: 可选用户标识，不传则查询所有咨询单。
    """
    from app.core.database import async_session
    from app.models.consultation import Consultation
    from sqlalchemy import select

    try:
        async with async_session() as db:
            query = select(Consultation).where(Consultation.id == consultation_id)

            # If user_id provided, restrict to that user's consultations
            if user_id:
                try:
                    uid = uuid.UUID(user_id)
                    query = query.where(Consultation.user_id == uid)
                except ValueError:
                    pass

            result = await db.execute(query)
            c = result.scalar_one_or_none()

        if c is None:
            return json.dumps({"error": "咨询单不存在"}, ensure_ascii=False)

        return json.dumps(
            {
                "id": str(c.id),
                "question": c.question,
                "draft_answer": c.draft_answer,
                "final_answer": c.final_answer,
                "status": c.status,
                "review_comment": c.review_comment,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "reviewed_at": c.reviewed_at.isoformat() if c.reviewed_at else None,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@mcp.tool()
async def list_knowledge_documents() -> str:
    """列出知识库中所有文档的名称、大小及向量化状态。

    返回信息包括文档 ID、文件名、文件大小、分块数、处理状态、错误信息等。
    """
    from app.core.database import async_session
    from app.models.knowledge import KnowledgeDocument
    from sqlalchemy import select

    try:
        async with async_session() as db:
            result = await db.execute(
                select(KnowledgeDocument).order_by(
                    KnowledgeDocument.created_at.desc()
                )
            )
            docs = result.scalars().all()

        results = []
        for d in docs:
            results.append({
                "id": str(d.id),
                "filename": d.filename,
                "file_size": d.file_size,
                "chunk_count": d.chunk_count,
                "status": d.status,
                "error": d.error,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            })

        return json.dumps(
            {"documents": results, "total": len(results)}, ensure_ascii=False
        )
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
