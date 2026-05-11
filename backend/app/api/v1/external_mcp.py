"""External MCP API — SSE transport routes.

External MCP clients (Cursor, Claude Desktop, Dify, etc.) connect via:

    GET  /api/v1/external-mcp/sse?token=<access_token>
    POST /api/v1/external-mcp/messages/?session_id=<id>

Authentication is optional and controlled via the EXTERNAL_MCP_AUTH_ENABLED
env var. When enabled, the SSE endpoint requires a valid JWT access token
as a query parameter.
"""

from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import Response
from typing import Optional

from app.mcp_servers.external_api_server import mcp as fastmcp_server
from app.core.config import get_settings
from app.core.security import decode_token
from mcp.server.sse import SseServerTransport

router = APIRouter()

# ── SSE transport ────────────────────────────────────────────────────────────

MESSAGE_ENDPOINT = "/api/v1/external-mcp/messages/"
sse_transport = SseServerTransport(MESSAGE_ENDPOINT)

# Get the underlying MCP Server from the FastMCP instance.
_mcp_server = fastmcp_server._mcp_server


async def _verify_token(token: Optional[str]) -> None:
    """Validate optional JWT token for external MCP access."""
    settings = get_settings()
    if not settings.jwt_secret_key:
        return  # No JWT configured, skip auth
    if not token:
        raise HTTPException(status_code=401, detail="Missing access token")
    payload = decode_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired access token")


# ── SSE endpoint ─────────────────────────────────────────────────────────────


@router.get("/sse")
async def external_mcp_sse(request: Request, token: Optional[str] = Query(None)):
    """SSE endpoint for MCP protocol.

    The client opens a GET connection to this endpoint. The SSE transport
    handles the protocol negotiation and bidirectional communication. Tool
    calls are dispatched to the FastMCP server registered in
    ``external_api_server.py``.
    """
    settings = get_settings()
    if settings.app_env != "development":
        await _verify_token(token)

    async with sse_transport.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        await _mcp_server.run(
            streams[0],
            streams[1],
            _mcp_server.create_initialization_options(),
        )

    return Response()


# ── Message endpoint ─────────────────────────────────────────────────────────


@router.post("/messages/")
async def external_mcp_messages(request: Request):
    """POST endpoint where the MCP client sends protocol messages."""
    await sse_transport.handle_post_message(
        request.scope, request.receive, request._send
    )
