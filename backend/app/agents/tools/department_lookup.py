"""Read-only routing lookup backed by existing ticket services."""

from sqlalchemy.orm import Session

from app.models import User
from app.services.tickets import list_assignable_users, list_departments


def get_routing_options(db: Session, user: User) -> tuple[list[dict], list[dict]]:
    """Return active departments and eligible staff, scoped by existing RBAC."""
    departments = [
        {
            "id": item.id,
            "name": item.name,
            "description": item.description,
        }
        for item in list_departments(db).items
    ]

    staff: list[dict] = []
    if user.role in {"staff", "hod", "admin"}:
        staff = [
            {
                "id": item.id,
                "name": item.full_name,
                "role": item.role,
                "department_id": item.department_id,
            }
            for item in list_assignable_users(db, user).items
            if item.role in {"staff", "hod"}
        ]
    return departments, staff
