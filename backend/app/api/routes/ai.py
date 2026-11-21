"""Authenticated AI assistance endpoints.

Students are blocked by the role dependency. Staff/HOD/admin requests are
additionally scoped by the existing per-ticket visibility service.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import require_staff_or_above
from app.db.dependencies import get_db
from app.models import User
from app.schemas.ai import AiAnalysisResponse, AiDraftApprovalResponse
from app.agents.services import agent_service

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post(
    "/tickets/{ticket_id}/analyze",
    response_model=AiAnalysisResponse,
    status_code=status.HTTP_201_CREATED,
)
def analyze_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_staff_or_above),
) -> AiAnalysisResponse:
    return agent_service.run_ticket_analysis(db, ticket_id, user)


@router.get("/tickets/{ticket_id}/analysis", response_model=AiAnalysisResponse)
def get_ticket_analysis(
    ticket_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_staff_or_above),
) -> AiAnalysisResponse:
    return agent_service.get_latest_analysis(db, ticket_id, user)


@router.post(
    "/tickets/{ticket_id}/draft",
    response_model=AiAnalysisResponse,
    status_code=status.HTTP_201_CREATED,
)
def regenerate_draft(
    ticket_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_staff_or_above),
) -> AiAnalysisResponse:
    return agent_service.run_ticket_analysis(db, ticket_id, user)


@router.post("/tickets/{ticket_id}/approve-draft", response_model=AiDraftApprovalResponse)
def approve_draft(
    ticket_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_staff_or_above),
) -> AiDraftApprovalResponse:
    return agent_service.approve_draft(db, ticket_id, user)
