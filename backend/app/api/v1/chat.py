"""Chat API — sessions, messages, and agent-powered streaming.

Uses ``create_agent`` (LangGraph) which handles the tool-calling loop natively.
Input / output format::

    inputs = {"messages": [HumanMessage(...), AIMessage(...), etc.]}
    result = await agent.ainvoke(inputs)
    answer = result["messages"][-1].content
"""

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
from pathlib import Path

from app.core.database import async_session, get_db
from app.core.langfuse import trace_agent_call
from app.middleware.disclaimer import add_disclaimer
from app.models.attachment import Attachment
from app.models.consultation import Consultation
from app.models.message import Message
from app.models.session import Session
from app.models.user import User
from app.rag.embeddings import get_embeddings
from app.schemas.chat import CreateSessionRequest, MessageInfo, RenameSessionRequest, SendMessageRequest, SessionInfo, AttachmentInfo
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
    messages = result.scalars().all()
    result_data = []
    for m in messages:
        info = _message_info(m)
        # Attachments are not re-loaded from history for token efficiency,
        # but the IDs are stored for reference
        result_data.append(info)
    return ApiResponse(data=result_data)


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

    Only fires when the matched portion covers most of the query —
    compound queries like "北京今天几号 什么天气" fall through to the agent
    so both date AND weather (via web search) are answered.
    """
    for pattern, _, tz in _FAST_PATH_PATTERNS:
        m = pattern.search(query)
        if m:
            # If there's substantial content outside the match, it's a compound
            # query — let the agent handle it with multi-tool chaining.
            before = query[:m.start()]
            after = query[m.end():]
            remainder = (before + after).strip()
            if len(remainder) > 3:
                return None
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
    await _save_user_message(db, session.id, req.content, attachment_ids=req.attachment_ids)

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

    # Build agent with tools from registry — tool list comes purely from config
    knowledge_enabled = bool(cfg.get("active_knowledge_ids"))
    registry = get_registry()
    active_ids = cfg.get("active_tool_ids", [])
    tools = registry.get_agent_tools(
        active_tool_ids=active_ids,
        active_mcp_ids=cfg.get("active_mcp_ids"),
        knowledge_enabled=knowledge_enabled,
    )
    system_prompt = cfg.get("system_prompt", "") or DEFAULT_SYSTEM_PROMPT
    agent = build_agent(tools, system_prompt)

    history = await _load_history(session, db)

    messages: list = [*history]
    if req.attachment_ids:
        attachment_texts = []
        for aid in req.attachment_ids:
            result = await db.execute(
                select(Attachment).where(Attachment.id == aid, Attachment.user_id == current_user.id)
            )
            att = result.scalar_one_or_none()
            if att and att.status == "ready":
                text = att.extracted_text or att.transcription or ""
                if text.strip():
                    attachment_texts.append(text)
        if attachment_texts:
            messages.append(SystemMessage(
                content=f"用户上传了文件，以下是通过OCR/文字提取得到的内容，请据此回答：\n\n"
                        + "\n\n---\n\n".join(attachment_texts)
            ))

    messages.append(HumanMessage(content=req.content))

    inputs = {"messages": messages}
    result = await agent.ainvoke(inputs)
    messages = result.get("messages", [])
    answer = _extract_answer(messages)
    answer = await add_disclaimer(answer)
    sources = _extract_sources(messages)

    # LangFuse trace
    langfuse_trace_id = await trace_agent_call(req.content, answer, user_id=str(current_user.id))

    if cacheable:
        _get_cache().set(req.content, {"answer": answer, "sources": sources})

    msg = await _save_assistant_message(db, session.id, answer, sources=sources)
    consultation = await _create_consultation(db, current_user, session.id, req.content, answer)
    if langfuse_trace_id:
        consultation.langfuse_trace_id = langfuse_trace_id

    session.summary = _make_summary(session.summary, req.content, answer)
    db.add(session)
    await db.commit()

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
    await _save_user_message(db, session.id, req.content, attachment_ids=req.attachment_ids)

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

    # Build agent with tools from registry.
    # The LLM decides when to call each tool via function calling.
    knowledge_enabled = bool(cfg.get("active_knowledge_ids"))
    registry = get_registry()
    active_ids = cfg.get("active_tool_ids", [])
    tools = registry.get_agent_tools(
        active_tool_ids=active_ids,
        active_mcp_ids=cfg.get("active_mcp_ids"),
        knowledge_enabled=knowledge_enabled,
    )
    system_prompt = cfg.get("system_prompt", "") or DEFAULT_SYSTEM_PROMPT
    agent = build_agent(tools, system_prompt)

    history = await _load_history(session, db)

    # Load attachment context before releasing the DB session
    attachment_contexts: list[str] = []
    if req.attachment_ids:
        result = await db.execute(
            select(Attachment).where(
                Attachment.id.in_([uuid.UUID(aid) for aid in req.attachment_ids]),
                Attachment.user_id == current_user.id,
            )
        )
        for att in result.scalars().all():
            if att.status == "ready":
                text = att.extracted_text or att.transcription or ""
                if text.strip():
                    attachment_contexts.append(text)

    # Release the DB session before streaming so the connection pool is not
    # exhausted during long LLM generations.
    current_summary = session.summary
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

            # Step 2 — Build messages with context
            messages = [*history]
            if attachment_contexts:
                messages.append(SystemMessage(
                    content=f"用户上传了文件，以下是通过OCR/文字提取得到的内容，请据此回答：\n\n"
                            + "\n\n---\n\n".join(attachment_contexts)
                ))
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

            # LangFuse trace
            langfuse_trace_id = await trace_agent_call(req.content, full_answer, user_id=str(current_user.id))

            if cacheable:
                _get_cache().set(req.content, {"answer": full_answer, "sources": sources})

            # Re-acquire DB session for persistence
            async with async_session() as new_db:
                msg = await _save_assistant_message(new_db, session_id, full_answer, sources=sources)
                consultation = await _create_consultation(
                    new_db, current_user, session_id, req.content, full_answer
                )
                if langfuse_trace_id:
                    consultation.langfuse_trace_id = langfuse_trace_id
                new_summary = _make_summary(current_summary, req.content, full_answer)
                s = (await new_db.execute(select(Session).where(Session.id == session_id))).scalar_one()
                s.summary = new_summary
                await new_db.commit()

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


def _make_summary(old_summary: str | None, question: str, answer: str) -> str:
    """Append current Q&A to summary using first 200 chars of answer."""
    answer_brief = answer[:200].replace("\n", " ")
    entry = f"用户：{question[:100]}\n助手：{answer_brief}"
    return f"{old_summary}\n\n{entry}" if old_summary else entry


async def _load_history(session: Session, db: AsyncSession) -> list:
    """Load history — use summary when over 20 rounds, else full messages."""
    result = await db.execute(
        select(Message).where(Message.session_id == session.id).order_by(Message.created_at)
    )
    messages = result.scalars().all()
    msg_count = len(messages)

    # Use summary only after 20 rounds (40 messages) to keep context accurate
    if msg_count >= 40 and session.summary:
        return [SystemMessage(content=f"以下是之前的对话摘要：\n{session.summary}")]

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


async def _save_user_message(
    db: AsyncSession,
    session_id: uuid.UUID,
    content: str,
    attachment_ids: list[str] | None = None,
):
    msg = Message(
        id=uuid.uuid4(),
        session_id=session_id,
        role="user",
        content=content,
        attachment_ids=attachment_ids or [],
    )
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


async def _load_attachments(db: AsyncSession, attachment_ids: list[str] | None) -> list[AttachmentInfo]:
    """Load attachment info for a list of attachment IDs."""
    if not attachment_ids:
        return []
    result = await db.execute(
        select(Attachment).where(Attachment.id.in_([uuid.UUID(aid) for aid in attachment_ids]))
    )
    atts = result.scalars().all()
    from app.core.config import get_settings
    uploads_parent = Path(get_settings().upload_storage_path).parent
    result_list = []
    for a in atts:
        url = ""
        try:
            rel = Path(a.file_path).relative_to(uploads_parent)
            url = f"/{rel}"
        except ValueError:
            pass
        result_list.append(AttachmentInfo(
            id=str(a.id),
            file_type=a.file_type,
            filename=a.filename,
            file_size=a.file_size,
            mime_type=a.mime_type,
            extracted_text=a.extracted_text,
            transcription=a.transcription,
            status=a.status,
            url=url,
            created_at=a.created_at.isoformat() if a.created_at else "",
        ))
    return result_list


def _message_info(m: Message) -> MessageInfo:
    return MessageInfo(
        id=str(m.id),
        session_id=str(m.session_id),
        role=m.role,
        content=m.content,
        sources=m.sources,
        created_at=m.created_at.isoformat() if m.created_at else "",
    )
