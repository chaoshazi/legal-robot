from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router
from app.api.v1.chat import router as chat_router
from app.api.v1.consultations import router as consultations_router
from app.api.v1.external_mcp import router as external_mcp_router
from app.api.v1.knowledge import router as knowledge_router
from app.api.v1.mcp import router as mcp_router
from app.api.v1.settings import router as settings_router
from app.api.v1.tools import router as tools_router
from app.api.v1.permissions import router as permissions_router
from app.api.v1.upload import router as upload_router
from app.api.v1.audit import router as audit_router
from app.api.v1.evaluations import router as evaluations_router

router = APIRouter()
router.include_router(auth_router, prefix="/auth", tags=["Auth"])
router.include_router(users_router, prefix="/users", tags=["Users"])
router.include_router(chat_router, prefix="/chat", tags=["Chat"])
router.include_router(consultations_router, prefix="/consultations", tags=["Consultations"])
router.include_router(knowledge_router, prefix="/knowledge", tags=["Knowledge"])
router.include_router(mcp_router, prefix="/mcp", tags=["MCP"])
router.include_router(settings_router, prefix="/settings", tags=["Settings"])
router.include_router(tools_router, prefix="/tools", tags=["Tools"])
router.include_router(permissions_router, prefix="/permissions", tags=["Permissions"])
router.include_router(external_mcp_router, prefix="/external-mcp", tags=["External MCP"])
router.include_router(audit_router, prefix="/audit-logs", tags=["Audit Logs"])
router.include_router(evaluations_router, prefix="/evaluations", tags=["Evaluations"])
router.include_router(upload_router, prefix="/chat", tags=["Chat"])
