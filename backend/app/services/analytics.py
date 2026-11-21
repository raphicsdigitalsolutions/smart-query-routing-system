"""Ticket analytics built exclusively from SQL aggregates over real rows.

Every number returned here is computed in the database from the same scope the
caller is allowed to see: admins see everything, HODs their department, and
staff the tickets assigned to them. No sample or placeholder data is used.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import and_, false, func, select

from app.core.enums import TicketPriority, TicketStatus
from app.models import Department, Ticket, TicketAiAnalysis, User
from app.schemas.analytics import (
    AnalyticsOverviewResponse,
    CategoryCount,
    DepartmentCount,
    MonthCount,
)

TICKET_CHANNELS = ("web", "email", "whatsapp")
BACKLOG_STATUSES = [
    TicketStatus.NEW.value,
    TicketStatus.ASSIGNED.value,
    TicketStatus.IN_PROGRESS.value,
    TicketStatus.WAITING_FOR_STUDENT.value,
]
BACKLOG_MONTHS = 6


def _scope_conditions(user: User) -> list[Any]:
    """Return the WHERE clauses that restrict analytics to the caller's scope."""
    if user.role == "admin":
        return []
    if user.role == "hod":
        if user.department_id is None:
            return [false()]  # no department => no rows, still real aggregates
        return [Ticket.department_id == user.department_id]
    if user.role == "staff":
        return [Ticket.assigned_to == user.id]
    return [false()]


def _scope_label(user: User) -> str:
    if user.role == "admin":
        return "all"
    if user.role == "hod":
        return f"department_id={user.department_id}"
    if user.role == "staff":
        return f"assigned_to={user.id}"
    return "none"


def _grouped_counts(
    db, column, allowed: list[str] | tuple[str, ...], conditions: list[Any]
) -> dict[str, int]:
    """COUNT(*) GROUP BY a ticket column, with every known key present."""
    result = {value: 0 for value in allowed}
    rows = db.execute(select(column, func.count(Ticket.id)).where(*conditions).group_by(column)).all()
    for key, count in rows:
        if key is not None:
            result[str(key)] = int(count)
    return result


def _average_first_response_minutes(db, dialect: str, conditions: list[Any]) -> float | None:
    """Average (first_response_at - created_at) in minutes, from stored timestamps."""
    with_response = [*conditions, Ticket.first_response_at.is_not(None)]
    if dialect == "sqlite":
        minutes = (func.julianday(Ticket.first_response_at) - func.julianday(Ticket.created_at)) * 24 * 60
    else:
        minutes = func.extract("epoch", Ticket.first_response_at - Ticket.created_at) / 60
    value = db.scalar(select(func.avg(minutes)).where(*with_response))
    return round(float(value), 2) if value is not None else None


def _department_breakdown(db, conditions: list[Any]) -> list[DepartmentCount]:
    rows = db.execute(
        select(Department.id, Department.name, func.count(Ticket.id))
        .join(Department, Ticket.department_id == Department.id)
        .where(*conditions)
        .group_by(Department.id, Department.name)
        .order_by(func.count(Ticket.id).desc(), Department.name)
    ).all()
    return [
        DepartmentCount(department_id=int(dept_id), department_name=name, total=int(total))
        for dept_id, name, total in rows
    ]


def _latest_ai_categories(db, dialect: str, conditions: list[Any]) -> list[CategoryCount]:
    """Group categories taken only from the newest analysis of each ticket."""
    latest = (
        select(
            TicketAiAnalysis.ticket_id,
            func.max(TicketAiAnalysis.version).label("latest_version"),
        )
        .group_by(TicketAiAnalysis.ticket_id)
        .subquery()
    )
    if dialect == "sqlite":
        category_expr = func.json_extract(TicketAiAnalysis.classification_json, "$.category")
    else:
        category_expr = TicketAiAnalysis.classification_json.op("->>")("category")

    rows = db.execute(
        select(category_expr.label("category"), func.count(func.distinct(Ticket.id)))
        .join(
            latest,
            and_(
                TicketAiAnalysis.ticket_id == latest.c.ticket_id,
                TicketAiAnalysis.version == latest.c.latest_version,
            ),
        )
        .join(Ticket, Ticket.id == TicketAiAnalysis.ticket_id)
        .where(*conditions)
        .group_by(category_expr)
        .order_by(func.count(func.distinct(Ticket.id)).desc(), category_expr)
    ).all()
    return [
        CategoryCount(category=str(category), total=int(total))
        for category, total in rows
        if category is not None
    ]


def _month_keys(now: datetime) -> list[tuple[int, int, str]]:
    """The last six calendar months, oldest first, as (year, month, YYYY-MM)."""
    keys: list[tuple[int, int, str]] = []
    for offset in range(BACKLOG_MONTHS - 1, -1, -1):
        year, month = now.year, now.month - offset
        while month <= 0:
            month += 12
            year -= 1
        keys.append((year, month, f"{year:04d}-{month:02d}"))
    return keys


def _monthly_volume(db, dialect: str, conditions: list[Any], now: datetime) -> list[MonthCount]:
    keys = _month_keys(now)
    first_year, first_month, _ = keys[0]
    window_start = datetime(first_year, first_month, 1, tzinfo=timezone.utc)

    if dialect == "sqlite":
        month_expr = func.strftime("%Y-%m", Ticket.created_at)
    else:
        month_expr = func.to_char(func.date_trunc("month", Ticket.created_at), "YYYY-MM")

    rows = db.execute(
        select(month_expr.label("month"), func.count(Ticket.id))
        .where(*conditions, Ticket.created_at >= window_start)
        .group_by(month_expr)
    ).all()
    counts = {str(month): int(total) for month, total in rows}
    return [MonthCount(month=key, total=counts.get(key, 0)) for _, _, key in keys]


def get_overview(db, user: User, *, at: datetime | None = None) -> AnalyticsOverviewResponse:
    """Compute the overview for ``user`` with a single, consistent scope."""
    generated_at = at or datetime.now(timezone.utc)
    if generated_at.tzinfo is None:
        generated_at = generated_at.replace(tzinfo=timezone.utc)

    dialect = db.get_bind().dialect.name
    conditions = _scope_conditions(user)

    total = db.scalar(select(func.count(Ticket.id)).where(*conditions)) or 0
    escalated = (
        db.scalar(
            select(func.count(Ticket.id)).where(*conditions, Ticket.is_escalated.is_(True))
        )
        or 0
    )
    resolved = (
        db.scalar(
            select(func.count(Ticket.id)).where(
                *conditions, Ticket.status == TicketStatus.RESOLVED.value
            )
        )
        or 0
    )
    backlog = (
        db.scalar(select(func.count(Ticket.id)).where(*conditions, Ticket.status.in_(BACKLOG_STATUSES)))
        or 0
    )

    return AnalyticsOverviewResponse(
        generated_at=generated_at,
        scope=_scope_label(user),
        role=user.role,
        total_tickets=int(total),
        status_counts=_grouped_counts(db, Ticket.status, [status.value for status in TicketStatus], conditions),
        priority_counts=_grouped_counts(
            db, Ticket.priority, [priority.value for priority in TicketPriority], conditions
        ),
        channel_counts=_grouped_counts(db, Ticket.channel, list(TICKET_CHANNELS), conditions),
        escalated_count=int(escalated),
        resolved_count=int(resolved),
        backlog_count=int(backlog),
        avg_first_response_minutes=_average_first_response_minutes(db, dialect, conditions),
        department_breakdown=_department_breakdown(db, conditions),
        ai_category_breakdown=_latest_ai_categories(db, dialect, conditions),
        monthly_volume=_monthly_volume(db, dialect, conditions, generated_at),
    )
