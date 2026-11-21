"""Admin-only reader for the shared audit log."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.dependencies import get_db
from app.models import User
from app.schemas.audit import AuditLogListResponse
from app.services.audit import list_audit_logs

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=AuditLogListResponse)
def get_audit_logs(
    actor_id: int | None = Query(default=None, gt=0),
    action: str | None = Query(default=None, max_length=80),
    entity_type: str | None = Query(default=None, max_length=50),
    entity_id: str | None = Query(default=None, max_length=50),
    date_from: datetime | None = Query(default=None, alias="from"),
    date_to: datetime | None = Query(default=None, alias="to"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> AuditLogListResponse:
    """Return real AuditLog rows; no synthetic authentication audits exist."""
    return list_audit_logs(
        db,
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        date_from=date_from,
        date_to=date_to,
        skip=skip,
        limit=limit,
    )
