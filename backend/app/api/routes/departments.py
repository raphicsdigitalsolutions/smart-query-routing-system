"""Department lookup for intake forms and admin maintenance."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import require_admin, get_current_user
from app.db.dependencies import get_db
from app.models import User
from app.schemas.ticket import (
    DepartmentCreate,
    DepartmentListResponse,
    DepartmentResponse,
    DepartmentUpdate,
)
from app.services.tickets import create_department, list_departments, update_department

router = APIRouter(prefix="/departments", tags=["departments"])


@router.get("", response_model=DepartmentListResponse)
def get_departments(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> DepartmentListResponse:
    return list_departments(db)


@router.post("", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
def post_department(
    payload: DepartmentCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> DepartmentResponse:
    return create_department(db, payload, admin)


@router.patch("/{department_id}", response_model=DepartmentResponse)
def patch_department(
    department_id: int,
    payload: DepartmentUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> DepartmentResponse:
    return update_department(db, department_id, payload, admin)
