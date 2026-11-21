"""Endpoint modules mounted by the versioned API router."""

from app.api.routes.ai import router as ai_router
from app.api.routes.analytics import router as analytics_router
from app.api.routes.announcements import router as announcements_router
from app.api.routes.auth import router as auth_router
from app.api.routes.audit import router as audit_router
from app.api.routes.departments import router as departments_router
from app.api.routes.integrations import router as integrations_router
from app.api.routes.knowledge import router as knowledge_router
from app.api.routes.leave import router as leave_router
from app.api.routes.notifications import router as notifications_router
from app.api.routes.oauth import router as oauth_router
from app.api.routes.operations import router as operations_router
from app.api.routes.reports import router as reports_router
from app.api.routes.settings import router as settings_router
from app.api.routes.status import router as status_router
from app.api.routes.tickets import router as tickets_router
from app.api.routes.users import router as users_router

__all__ = [
    "ai_router",
    "analytics_router",
    "announcements_router",
    "auth_router",
    "audit_router",
    "departments_router",
    "integrations_router",
    "knowledge_router",
    "leave_router",
    "notifications_router",
    "oauth_router",
    "operations_router",
    "reports_router",
    "settings_router",
    "status_router",
    "tickets_router",
    "users_router",
]
