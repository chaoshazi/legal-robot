from pydantic import BaseModel


class MCPServerCreate(BaseModel):
    name: str
    transport: str = "stdio"
    command: str | None = None
    args: str | None = None
    url: str | None = None
    api_key: str | None = None
    description: str | None = None


class MCPServerUpdate(BaseModel):
    name: str | None = None
    transport: str | None = None
    command: str | None = None
    args: str | None = None
    url: str | None = None
    api_key: str | None = None
    description: str | None = None
    enabled: bool | None = None


class MCPServerInfo(BaseModel):
    id: str
    name: str
    transport: str
    command: str | None
    args: str | None
    url: str | None
    description: str | None
    status: str
    enabled: bool
    created_at: str
    updated_at: str
