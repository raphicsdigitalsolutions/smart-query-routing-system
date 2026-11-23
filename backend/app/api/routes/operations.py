"""Administrative operations endpoints (SLA sweep and maintenance)."""

import secrets

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core.config import settings
from app.core.errors import AppError
from app.db.dependencies import get_db
from app.models import User
from app.schemas.integrations import EscalationRunResponse
from app.services.escalation import run_escalation_sweep

router = APIRouter(tags=["operations"])


@router.post("/tickets/escalation/run", response_model=EscalationRunResponse)
def run_escalation(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> EscalationRunResponse:
    result = run_escalation_sweep(db)
    return EscalationRunResponse(scanned=result["scanned"], escalated=result["escalated"])


@router.post("/tickets/escalation/sweep", response_model=EscalationRunResponse)
def run_escalation_sweep_cron(
    db: Session = Depends(get_db),
    x_cron_secret: str | None = Header(default=None, alias="X-Cron-Secret"),
) -> EscalationRunResponse:
    """Serverless-compatible SLA sweep trigger for an external cron/scheduler.

    The endpoint is disabled until ESCALATION_CRON_SECRET is configured. The
    secret is compared in constant time and never logged.
    """
    configured = (settings.ESCALATION_CRON_SECRET or "").strip()
    if not configured:
        raise AppError(
            "Escalation cron trigger is not configured",
            503,
            code="escalation_cron_not_configured",
        )
    provided = (x_cron_secret or "").strip()
    if not provided or not secrets.compare_digest(provided, configured):
        raise AppError("Invalid cron secret", 401, code="invalid_cron_secret")

    result = run_escalation_sweep(db)
    return EscalationRunResponse(scanned=result["scanned"], escalated=result["escalated"])
