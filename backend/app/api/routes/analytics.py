"""Real SQL-backed ticket analytics (staff and above)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_staff_or_above
from app.db.dependencies import get_db
from app.models import User
from app.schemas.analytics import AnalyticsOverviewResponse
from app.services.analytics import get_overview

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview", response_model=AnalyticsOverviewResponse)
def get_analytics_overview(
    db: Session = Depends(get_db),
    user: User = Depends(require_staff_or_above),
) -> AnalyticsOverviewResponse:
    """Aggregate the tickets this role may see; HODs are department-scoped."""
    return get_overview(db, user)
