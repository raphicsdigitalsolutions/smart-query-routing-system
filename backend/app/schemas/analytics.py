"""Response contracts for real-SQL ticket analytics."""

from datetime import datetime

from pydantic import BaseModel


class DepartmentCount(BaseModel):
    department_id: int
    department_name: str
    total: int


class CategoryCount(BaseModel):
    """A category from the latest AI analysis of a ticket."""

    category: str
    total: int


class MonthCount(BaseModel):
    """Ticket volume for one calendar month, keyed as YYYY-MM."""

    month: str
    total: int


class AnalyticsOverviewResponse(BaseModel):
    success: bool = True
    generated_at: datetime
    scope: str
    role: str
    total_tickets: int
    status_counts: dict[str, int]
    priority_counts: dict[str, int]
    channel_counts: dict[str, int]
    escalated_count: int
    resolved_count: int
    backlog_count: int
    avg_first_response_minutes: float | None = None
    department_breakdown: list[DepartmentCount]
    ai_category_breakdown: list[CategoryCount]
    monthly_volume: list[MonthCount]
