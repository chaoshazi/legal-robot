import uuid
from datetime import datetime

from pydantic import BaseModel


class SessionInfo(BaseModel):
    id: str
    title: str
    status: str
    created_at: str
    updated_at: str


class AttachmentInfo(BaseModel):
    id: str
    file_type: str
    filename: str
    file_size: int
    mime_type: str
    extracted_text: str | None = None
    transcription: str | None = None
    status: str
    url: str = ""
    created_at: str


class MessageInfo(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    sources: list | dict | None
    attachments: list[AttachmentInfo] = []
    created_at: str


class CreateSessionRequest(BaseModel):
    title: str = "新会话"


class RenameSessionRequest(BaseModel):
    title: str


class SendMessageRequest(BaseModel):
    session_id: str
    content: str
    enable_web_search: bool = True
    attachment_ids: list[str] = []


class UploadAttachmentResponse(BaseModel):
    id: str
    filename: str
    file_size: int
    file_type: str
    mime_type: str
    status: str
    url: str = ""
