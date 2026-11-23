"""Deterministic instructor selection for automatically routed tickets.

The project has no expertise, capacity or availability tables. Eligibility is
therefore defined only by persisted department membership, active-user state
and active leave windows. Workload balancing uses the number of non-terminal
tickets already assigned to each eligible staff member, with stable name and
id tie-breaks so the same database state always produces the same choice.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import InstructorLeave, Ticket, User

_OPEN_STATUSES = (
    "new",
    "assigned",
    "in_progress",
    "waiting_for_student",
)
_SELECTED_REASON = "least_open_workload_then_full_name_then_id"
_NO_ELIGIBLE_REASON = "no_eligible_instructor"


@dataclass(frozen=True)
class InstructorRoutingDecision:
    """Auditable result of one instructor-selection attempt."""

    instructor: User | None
    reason: str
    eligible_count: int
    excluded_on_leave_count: int
    excluded_inactive_count: int
    active_load: int | None = None


def _moment(at: datetime | None) -> datetime:
    """Return a UTC-aware reference time for leave-window comparisons."""
    moment = at or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


def resolve_instructor(
    db: Session,
    *,
    department_id: int,
    at: datetime | None = None,
) -> InstructorRoutingDecision:
    """Pick the least-loaded available staff instructor in a department.

    HOD and admin users are deliberately excluded: they are manual assignment
    and escalation targets, not the ordinary instructor queue. Tickets in
    terminal statuses do not contribute to workload.
    """
    department_staff = db.scalars(
        select(User)
        .where(
            User.role == "staff",
            User.department_id == department_id,
        )
        .order_by(User.id)
    ).all()

    excluded_inactive_count = sum(1 for user in department_staff if not user.is_active)
    active_staff = [user for user in department_staff if user.is_active]
    if not active_staff:
        return InstructorRoutingDecision(
            instructor=None,
            reason=_NO_ELIGIBLE_REASON,
            eligible_count=0,
            excluded_on_leave_count=0,
            excluded_inactive_count=excluded_inactive_count,
        )

    active_ids = [user.id for user in active_staff]
    moment = _moment(at)
    # The end bound is exclusive, matching active_auto_reply(): a leave window
    # stops applying exactly at end_at.
    on_leave_ids = set(
        db.scalars(
            select(InstructorLeave.user_id).where(
                InstructorLeave.is_active.is_(True),
                InstructorLeave.user_id.in_(active_ids),
                InstructorLeave.start_at <= moment,
                InstructorLeave.end_at > moment,
            )
        ).all()
    )

    eligible = [user for user in active_staff if user.id not in on_leave_ids]
    excluded_on_leave_count = len(on_leave_ids)
    if not eligible:
        return InstructorRoutingDecision(
            instructor=None,
            reason=_NO_ELIGIBLE_REASON,
            eligible_count=0,
            excluded_on_leave_count=excluded_on_leave_count,
            excluded_inactive_count=excluded_inactive_count,
        )

    eligible_ids = [user.id for user in eligible]
    workload_rows = db.execute(
        select(Ticket.assigned_to, func.count(Ticket.id))
        .where(
            Ticket.assigned_to.in_(eligible_ids),
            Ticket.status.in_(_OPEN_STATUSES),
        )
        .group_by(Ticket.assigned_to)
    ).all()
    workloads = {user_id: count for user_id, count in workload_rows}

    selected = min(
        eligible,
        key=lambda user: (
            workloads.get(user.id, 0),
            (user.full_name or "").lower(),
            user.id,
        ),
    )
    return InstructorRoutingDecision(
        instructor=selected,
        reason=_SELECTED_REASON,
        eligible_count=len(eligible),
        excluded_on_leave_count=excluded_on_leave_count,
        excluded_inactive_count=excluded_inactive_count,
        active_load=workloads.get(selected.id, 0),
    )
