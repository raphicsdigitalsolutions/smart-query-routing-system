"""Administrative operations endpoints (SLA sweep and maintenance)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_admin
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
