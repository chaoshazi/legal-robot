import uuid
from datetime import datetime

from pydantic import BaseModel


class SessionInfo(BaseModel):
    id: str
    title: str
    status: str
    created_at: str
    updated_at: str


class MessageInfo(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    sources: list | dict | None
    created_at: str


class CreateSessionRequest(BaseModel):
    title: str = "新会话"


class RenameSessionRequest(BaseModel):
    title: str


class SendMessageRequest(BaseModel):
    session_id: str
    content: str
    enable_web_search: bool = True
