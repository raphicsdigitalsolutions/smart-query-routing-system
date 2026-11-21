"""Shared domain enumerations.

Values are lowercase because that matches the existing database convention;
member names are uppercase so API documentation and logs read naturally.
"""

from enum import Enum


class UserRole(str, Enum):
    STUDENT = "student"
    STAFF = "staff"
    HOD = "hod"
    ADMIN = "admin"


class TicketStatus(str, Enum):
    NEW = "new"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    WAITING_FOR_STUDENT = "waiting_for_student"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


# Controlled lifecycle. A missing key means the status is terminal.
STATUS_TRANSITIONS: dict[TicketStatus, set[TicketStatus]] = {
    TicketStatus.NEW: {TicketStatus.ASSIGNED, TicketStatus.IN_PROGRESS, TicketStatus.CLOSED},
    TicketStatus.ASSIGNED: {
        TicketStatus.IN_PROGRESS,
        TicketStatus.WAITING_FOR_STUDENT,
        TicketStatus.RESOLVED,
        TicketStatus.NEW,
    },
    TicketStatus.IN_PROGRESS: {
        TicketStatus.WAITING_FOR_STUDENT,
        TicketStatus.RESOLVED,
        TicketStatus.ASSIGNED,
    },
    TicketStatus.WAITING_FOR_STUDENT: {
        TicketStatus.IN_PROGRESS,
        TicketStatus.RESOLVED,
        TicketStatus.CLOSED,
    },
    TicketStatus.RESOLVED: {TicketStatus.CLOSED, TicketStatus.IN_PROGRESS},
    TicketStatus.CLOSED: set(),
}

# Staff may only make operational progress transitions. Reassignment back to
# NEW and escalations remain with HOD/admin.
STAFF_ALLOWED_TRANSITIONS: set[TicketStatus] = {
    TicketStatus.IN_PROGRESS,
    TicketStatus.WAITING_FOR_STUDENT,
    TicketStatus.RESOLVED,
    TicketStatus.CLOSED,
}
