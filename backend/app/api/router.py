"""Aggregates all versioned API routers.

Mounted once in ``app.main`` under ``settings.API_V1_PREFIX``.
"""

from fastapi import APIRouter

from app.api.routes import (
    ai_router,
    analytics_router,
    announcements_router,
    auth_router,
    audit_router,
    departments_router,
    integrations_router,
    knowledge_router,
    leave_router,
    notifications_router,
    oauth_router,
    operations_router,
    reports_router,
    settings_router,
    status_router,
    tickets_router,
    users_router,
)

api_router = APIRouter()
api_router.include_router(ai_router)
api_router.include_router(status_router)
api_router.include_router(auth_router)
api_router.include_router(oauth_router)
api_router.include_router(departments_router)
api_router.include_router(users_router)
api_router.include_router(tickets_router)
api_router.include_router(settings_router)
api_router.include_router(knowledge_router)
api_router.include_router(notifications_router)
api_router.include_router(analytics_router)
api_router.include_router(announcements_router)
api_router.include_router(leave_router)
api_router.include_router(audit_router)
api_router.include_router(reports_router)
api_router.include_router(integrations_router)
api_router.include_router(operations_router)
