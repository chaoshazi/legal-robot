"""Chat API — sessions, messages, and agent-powered streaming.

Uses ``create_agent`` (LangGraph) which handles the tool-calling loop natively.
Input / output format::

    inputs = {"messages": [HumanMessage(...), AIMessage(...), etc.]}
    result = await agent.ainvoke(inputs)
    answer = result["messages"][-1].content
"""

import asyncio
import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from app.api.deps import get_current_user
from app.agent.agent import build_agent, DEFAULT_SYSTEM_PROMPT
from app.agent.cache import SemanticCache
from app.agent.config import get_agent_config
from app.agent.registry import get_registry
from app.core.database import async_session, get_db
from app.middleware.disclaimer import add_disclaimer
from app.rag.retriever import async_get_retriever
from app.models.consultation import Consultation
from app.models.message import Message
from app.models.session import Session
from app.models.user import User
from app.rag.embeddings import get_embeddings
from app.schemas.chat import CreateSessionRequest, MessageInfo, RenameSessionRequest, SendMessageRequest, SessionInfo
from app.schemas.common import ApiResponse

router = APIRouter()

_cache: SemanticCache | None = None

# ── Cache helpers ────────────────────────────────────────────────────────


def _get_cache() -> SemanticCache:
    global _cache
    if _cache is None:
        _cache = SemanticCache(get_embeddings())
    return _cache


def _is_cacheable(cfg: dict) -> bool:
    """Only cache pure LLM Q&A — skip if any tools/MCP/knowledge is active
    OR if builtin tools are loaded (calculate_compensation always exists)."""
    # Builtin tools are always loaded, so caching can't know if a query
    # will trigger tool calls. Disable cache to prevent stale blob delivery.
    return False


# ── Session CRUD ─────────────────────────────────────────────────────────


@router.post("/sessions")
async def create_session(
    req: CreateSessionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = Session(id=uuid.uuid4(), user_id=current_user.id, title=req.title)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return ApiResponse(data=_session_info(session))


@router.put("/sessions/{session_id}")
async def rename_session(
    session_id: str,
    req: RenameSessionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Session).where(Session.id == session_id, Session.user_id == current_user.id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    session.title = req.title
    await db.commit()
    await db.refresh(session)
    return ApiResponse(data=_session_info(session))


@router.get("/sessions")
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Session)
        .where(Session.user_id == current_user.id)
        .order_by(Session.updated_at.desc())
    )
    return ApiResponse(data=[_session_info(s) for s in result.scalars().all()])


@router.get("/sessions/{session_id}/messages")
async def list_messages(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Message).where(Message.session_id == session_id).order_by(Message.created_at)
    )
    return ApiResponse(data=[_message_info(m) for m in result.scalars().all()])


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Session).where(Session.id == session_id, Session.user_id == current_user.id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    await db.execute(delete(Consultation).where(Consultation.session_id == session_id))
    await db.execute(delete(Message).where(Message.session_id == session_id))
    await db.delete(session)
    await db.commit()
    return ApiResponse(data=None)


# ── Source extraction helpers ────────────────────────────────────────────


def _extract_sources(messages: list) -> list[dict]:
    """Extract tool-call metadata from an agent response message list."""
    sources: list[dict] = []
    for m in messages:
        if isinstance(m, ToolMessage):
            sources.append({
                "type": "tool_call",
                "tool": getattr(m, "name", "") or "",
                "content": (m.content or "")[:300],
            })
    return sources


def _extract_answer(messages: list) -> str:
    """Extract the final answer from the agent response message list."""
    for m in reversed(messages):
        if isinstance(m, AIMessage) and m.content:
            return m.content
    return ""


# ── Pre-retrieval: always search KB before each turn ─────────────────────

_kb_available: bool | None = None


async def _check_kb() -> bool:
    """Quick check whether the knowledge base has data.

    Once confirmed positive, caches permanently (no more Qdrant pings).
    A negative result is re-checked every time so newly ingested docs
    are picked up promptly.
    """
    global _kb_available
    if _kb_available:               # True — definitely has data
        return True
    if _kb_available is False:       # already failed once this session
        return False
    # _kb_available is None → first call, check Qdrant
    try:
        from qdrant_client import QdrantClient
        from app.core.config import get_settings
        s = get_settings()
        client = QdrantClient(url=s.qdrant_url, timeout=2.0)
        loop = asyncio.get_running_loop()
        count = await loop.run_in_executor(None, lambda: client.count(collection_name=s.qdrant_collection))
        _kb_available = count.count > 0
    except Exception:
        _kb_available = False
    return _kb_available


async def _retrieve_context(query: str, doc_ids: list[str] | None = None) -> str | None:
    """Search knowledge base and return formatted context, or None if unavailable/empty."""
    if not await _check_kb():
        return None
    try:
        retriever = await async_get_retriever()
        docs = await asyncio.wait_for(retriever.ainvoke(query, doc_ids=doc_ids), timeout=10.0)
        if not docs:
            return None
        parts = []
        for i, d in enumerate(docs, 1):
            source = d.metadata.get("source", "法律知识库")
            parts.append(f"[{i}] 来自《{source}》\n{d.page_content}")
        return "\n\n".join(parts)
    except Exception:
        import logging
        logging.getLogger("chat.retrieve").exception("KB search failed")
        return None


# ── Fast-path: skip LLM for trivial queries ──────────────────────────────

_FAST_PATH_PATTERNS: list[tuple[re.Pattern, str, str]] = [
    # (pattern, tool_name, tz_arg)
    (re.compile(r"(今天|当前|现在).*(几号|日期|什么日子)"), "get_current_datetime", "Asia/Shanghai"),
    (re.compile(r"(星期几|周几|礼拜几)"), "get_current_datetime", "Asia/Shanghai"),
    (re.compile(r"^今天$|^日期$|^星期$|^时间$|^现在$"), "get_current_datetime", "Asia/Shanghai"),
    (re.compile(r"(现在|当前).*(几点|时间)"), "get_current_datetime", "Asia/Shanghai"),
    (re.compile(r"^(几点了|几点啦|几点钟)$"), "get_current_datetime", "Asia/Shanghai"),
]


def _try_fast_path(query: str) -> str | None:
    """Handle trivial queries without invoking the LLM.

    Returns the answer string if matched, or None to fall through to the agent.
    """
    for pattern, _, tz in _FAST_PATH_PATTERNS:
        if pattern.search(query):
            from app.agent.tools import get_current_datetime
            result = get_current_datetime.invoke({"timezone": tz})
            return result if isinstance(result, str) else str(result)
    return None


# ── Non-streaming /ask ───────────────────────────────────────────────────


@router.post("/ask")
async def ask(
    req: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await _get_session(db, req.session_id, current_user.id)
    await _save_user_message(db, session.id, req.content)

    cfg = get_agent_config()
    cacheable = _is_cacheable(cfg)

    # Cache hit
    if cacheable:
        cache = _get_cache()
        cached = cache.get(req.content)
        if cached:
            answer, sources = cached["answer"], cached.get("sources", [])
            answer = await add_disclaimer(answer)
            msg = await _save_assistant_message(db, session.id, answer, sources=sources)
            consultation = await _create_consultation(db, current_user, session.id, req.content, answer)
            return ApiResponse(data={
                "answer": answer,
                "message_id": str(msg.id),
                "consultation_id": str(consultation.id),
                "status": consultation.status,
                "sources": sources,
            })

    # Fast-path: handle trivial queries without LLM
    fast_answer = _try_fast_path(req.content)
    if fast_answer:
        answer = await add_disclaimer(fast_answer)
        msg = await _save_assistant_message(db, session.id, answer)
        consultation = await _create_consultation(db, current_user, session.id, req.content, answer)
        return ApiResponse(data={
            "answer": answer,
            "message_id": str(msg.id),
            "consultation_id": str(consultation.id),
            "status": consultation.status,
            "sources": [],
        })

    # Build agent with tools from registry
    knowledge_enabled = bool(cfg.get("active_knowledge_ids"))
    registry = get_registry()
    tools = registry.get_agent_tools(
        active_tool_ids=cfg.get("active_tool_ids"),
        active_mcp_ids=cfg.get("active_mcp_ids"),
        knowledge_enabled=knowledge_enabled,
    )
    system_prompt = cfg.get("system_prompt", "") or DEFAULT_SYSTEM_PROMPT
    agent = build_agent(tools, system_prompt)

    history = await _load_history(db, session.id)

    # Pre-retrieval: inject KB context so the agent can't skip searching
    if knowledge_enabled:
        kb_context = await _retrieve_context(req.content, doc_ids=cfg.get("active_knowledge_ids"))
    else:
        kb_context = None
    messages: list = [*history]
    if kb_context:
        messages.append(SystemMessage(content=f"以下是知识库中检索到的相关法律条文，请基于这些内容回答用户问题：\n\n{kb_context}"))
    elif knowledge_enabled:
        messages.append(SystemMessage(content="知识库检索结果为空，未找到与用户问题相关的法律条文。"))
    messages.append(HumanMessage(content=req.content))

    inputs = {"messages": messages}
    result = await agent.ainvoke(inputs)
    messages = result.get("messages", [])
    answer = _extract_answer(messages)
    answer = await add_disclaimer(answer)
    sources = _extract_sources(messages)

    if cacheable:
        _get_cache().set(req.content, {"answer": answer, "sources": sources})

    msg = await _save_assistant_message(db, session.id, answer, sources=sources)
    consultation = await _create_consultation(db, current_user, session.id, req.content, answer)

    return ApiResponse(data={
        "answer": answer,
        "message_id": str(msg.id),
        "consultation_id": str(consultation.id),
        "status": consultation.status,
        "sources": sources,
    })


# ── SSE streaming /stream ───────────────────────────────────────────────


@router.post("/stream")
async def chat_stream(
    req: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await _get_session(db, req.session_id, current_user.id)
    await _save_user_message(db, session.id, req.content)

    cfg = get_agent_config()
    cacheable = _is_cacheable(cfg)

    # Cache hit (fast path)
    if cacheable:
        cache = _get_cache()
        cached = cache.get(req.content)
        if cached:
            answer, sources = cached["answer"], cached.get("sources", [])
            answer = await add_disclaimer(answer)
            msg = await _save_assistant_message(db, session.id, answer, sources=sources)
            consultation = await _create_consultation(db, current_user, session.id, req.content, answer)

            async def from_cache():
                yield f"data: {json.dumps({'token': answer, 'done': False})}\n\n"
                yield f"data: {json.dumps({'done': True, 'message_id': str(msg.id), 'consultation_id': str(consultation.id), 'status': consultation.status, 'sources': sources})}\n\n"
            return StreamingResponse(from_cache(), media_type="text/event-stream")

    # Build agent with tools from registry
    knowledge_enabled = bool(cfg.get("active_knowledge_ids"))
    registry = get_registry()
    tools = registry.get_agent_tools(
        active_tool_ids=cfg.get("active_tool_ids"),
        active_mcp_ids=cfg.get("active_mcp_ids"),
        knowledge_enabled=knowledge_enabled,
    )
    system_prompt = cfg.get("system_prompt", "") or DEFAULT_SYSTEM_PROMPT
    agent = build_agent(tools, system_prompt)

    history = await _load_history(db, session.id)

    # Release the DB session before streaming so the connection pool is not
    # exhausted during long LLM generations.
    session_id = session.id
    await db.close()

    async def generate() -> AsyncGenerator[str, None]:
        nonlocal history
        full_answer = ""
        full_reasoning = ""
        sources: list[dict] = []
        pending_tools: set[str] = set()

        try:
            # Step 0 — Fast-path: handle trivial queries without LLM
            fast_answer = _try_fast_path(req.content)
            if fast_answer:
                full_answer = await add_disclaimer(fast_answer)
                async with async_session() as new_db:
                    msg = await _save_assistant_message(new_db, session_id, full_answer)
                    consultation = await _create_consultation(
                        new_db, current_user, session_id, req.content, full_answer
                    )
                yield f"data: {json.dumps({'token': fast_answer, 'done': False})}\n\n"
                yield f"data: {json.dumps({'done': True, 'message_id': str(msg.id), 'consultation_id': str(consultation.id), 'status': consultation.status, 'sources': []})}\n\n"
                return

            # Step 1 — Search knowledge base (visible in frontend as a tool call)
            if knowledge_enabled:
                yield f"data: {json.dumps({'tool_start': 'search_knowledge_base', 'done': False})}\n\n"
                kb_context = await _retrieve_context(req.content, doc_ids=cfg.get("active_knowledge_ids"))
                yield f"data: {json.dumps({'tool_end': 'search_knowledge_base', 'done': False})}\n\n"
            else:
                kb_context = None

            # Step 2 — Build messages with KB context
            messages = [*history]
            if kb_context:
                messages.append(SystemMessage(content=f"以下是知识库中检索到的相关法律条文，请基于这些内容回答用户问题：\n\n{kb_context}"))
            elif knowledge_enabled:
                messages.append(SystemMessage(content="知识库检索结果为空，未找到与用户问题相关的法律条文。"))
            messages.append(HumanMessage(content=req.content))
            inputs = {"messages": messages}

            # Step 3 — Stream LLM response
            async for chunk, metadata in agent.astream(inputs, stream_mode="messages"):
                node = metadata.get("langgraph_node", "")

                if node == "model" and hasattr(chunk, "content"):
                    # Reasoning content (DeepSeek R1)
                    reasoning = chunk.additional_kwargs.get("reasoning_content", "") or ""
                    if reasoning:
                        full_reasoning += reasoning
                        yield f"data: {json.dumps({'reasoning': reasoning, 'done': False})}\n\n"

                    # Token streaming from LLM
                    token = chunk.content or ""
                    if token:
                        full_answer += token
                        yield f"data: {json.dumps({'token': token, 'done': False})}\n\n"

                    # Model decided to call a tool
                    tc_chunks = getattr(chunk, "tool_call_chunks", None) or []
                    for tc in tc_chunks:
                        name = tc.get("name", "")
                        if name and name not in pending_tools:
                            pending_tools.add(name)
                            yield f"data: {json.dumps({'tool_start': name, 'done': False})}\n\n"

                elif isinstance(chunk, ToolMessage):
                    # Tool execution completed
                    tool_name = getattr(chunk, "name", "") or ""
                    pending_tools.discard(tool_name)
                    sources.append({
                        "type": "tool_call",
                        "tool": tool_name,
                        "content": (chunk.content or "")[:300],
                    })
                    yield f"data: {json.dumps({'tool_end': tool_name, 'done': False})}\n\n"

            # Agent done — apply disclaimer & persist
            full_answer = await add_disclaimer(full_answer)

            if cacheable:
                _get_cache().set(req.content, {"answer": full_answer, "sources": sources})

            # Re-acquire DB session for persistence
            async with async_session() as new_db:
                msg = await _save_assistant_message(new_db, session_id, full_answer, sources=sources)
                consultation = await _create_consultation(
                    new_db, current_user, session_id, req.content, full_answer
                )

            done_data = {
                "done": True,
                "reasoning": full_reasoning,
                "message_id": str(msg.id),
                "consultation_id": str(consultation.id),
                "status": consultation.status,
                "sources": sources,
            }
            yield f"data: {json.dumps(done_data)}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


# ── Helpers ──────────────────────────────────────────────────────────────


async def _load_history(db: AsyncSession, session_id: uuid.UUID) -> list:
    """Load previous messages as LangChain message list (excludes last msg)."""
    result = await db.execute(
        select(Message).where(Message.session_id == session_id).order_by(Message.created_at)
    )
    messages = result.scalars().all()
    history = []
    for msg in messages[:-1]:  # exclude current input (already saved)
        if msg.role == "user":
            history.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            history.append(AIMessage(content=msg.content))
    return history


async def _get_session(db: AsyncSession, session_id: str, user_id: uuid.UUID) -> Session:
    result = await db.execute(
        select(Session).where(Session.id == session_id, Session.user_id == user_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session


async def _save_user_message(db: AsyncSession, session_id: uuid.UUID, content: str):
    msg = Message(id=uuid.uuid4(), session_id=session_id, role="user", content=content)
    db.add(msg)
    await db.commit()


async def _save_assistant_message(
    db: AsyncSession,
    session_id: uuid.UUID,
    content: str,
    sources: list | None = None,
) -> Message:
    msg = Message(
        id=uuid.uuid4(),
        session_id=session_id,
        role="assistant",
        content=content,
        sources=sources,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg


async def _create_consultation(
    db: AsyncSession,
    user: User,
    session_id: uuid.UUID,
    question: str,
    answer: str,
) -> Consultation:
    role_name = user.role.name if user.role else ""
    consultation = Consultation(
        id=uuid.uuid4(),
        user_id=user.id,
        session_id=session_id,
        question=question,
        draft_answer=answer,
        status="published" if role_name in ("lawyer", "admin") else "draft",
    )
    db.add(consultation)
    await db.commit()
    await db.refresh(consultation)
    return consultation


def _session_info(s: Session) -> SessionInfo:
    return SessionInfo(
        id=str(s.id),
        title=s.title,
        status=s.status,
        created_at=s.created_at.isoformat() if s.created_at else "",
        updated_at=s.updated_at.isoformat() if s.updated_at else "",
    )


def _message_info(m: Message) -> MessageInfo:
    return MessageInfo(
        id=str(m.id),
        session_id=str(m.session_id),
        role=m.role,
        content=m.content,
        sources=m.sources,
        created_at=m.created_at.isoformat() if m.created_at else "",
    )
