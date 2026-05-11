import uuid
from datetime import datetime

from pydantic import BaseModel


class ToolInfo(BaseModel):
    id: str
    name: str
    description: str
    function_name: str
    parameters: str | None
    tool_type: str
    enabled: bool
    created_at: str
    updated_at: str


class CreateToolRequest(BaseModel):
    name: str
    description: str = ""
    function_name: str
    parameters: str | None = None
    tool_type: str = "custom"
    enabled: bool = True


class UpdateToolRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    function_name: str | None = None
    parameters: str | None = None
    tool_type: str | None = None
    enabled: bool | None = None
