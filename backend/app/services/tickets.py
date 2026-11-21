"""Ticket business logic, authorization and transactional workflow."""

import secrets
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.enums import (
    STAFF_ALLOWED_TRANSITIONS,
    STATUS_TRANSITIONS,
    TicketPriority,
    TicketStatus,
)
from app.core.errors import AppError, NotFoundError
from app.models import (
    Department,
    Message,
    Ticket,
    TicketAssignmentHistory,
    TicketStatusHistory,
    User,
)
from app.schemas.ticket import (
    AssignableUserListResponse,
    AssignableUserResponse,
    AssignmentHistoryResponse,
    DepartmentCreate,
    DepartmentListResponse,
    DepartmentResponse,
    DepartmentUpdate,
    MessageCreate,
    MessageListResponse,
    MessageResponse,
    MutationResponse,
    StatusHistoryResponse,
    TicketCreate,
    TicketHistoryResponse,
    TicketListResponse,
    TicketResponse,
    TicketUpdate,
)
from app.services.audit import record_audit
from app.services.auto_routing import resolve_department
from app.services.notifications import (
    AUTO_REPLY,
    PUBLIC_REPLY,
    TICKET_ASSIGNED,
    TICKET_CLOSED,
    TICKET_CREATED,
    TICKET_RESOLVED,
    notify_ticket_event,
    utc_now,
)

try:  # optional companion module; absence must not break ticket operations
    from app.services.leave import active_auto_reply
except ImportError:  # pragma: no cover - depends on deployment composition
    active_auto_reply = None  # type: ignore[assignment]

ASSIGNABLE_ROLES = {"staff", "hod", "admin"}
ADMIN_FIELDS = {"department_id"}


def _public_reference() -> str:
    return f"TKT-{secrets.token_hex(4).upper()}"


def _ticket_response(ticket: Ticket) -> TicketResponse:
    """Serialize a ticket without ever including sensitive user fields."""
    return TicketResponse(
        id=ticket.id,
        public_reference=ticket.public_reference,
        subject=ticket.subject,
        description=ticket.description,
        category=ticket.category,
        priority=ticket.priority,
        status=ticket.status,
        is_escalated=ticket.is_escalated,
        student_id=ticket.student_id,
        assigned_to=ticket.assigned_to,
        department_id=ticket.department_id,
        student_name=ticket.student.full_name if ticket.student else None,
        assignee_name=ticket.assignee.full_name if ticket.assignee else None,
        department_name=ticket.department.name if ticket.department else None,
        channel=ticket.channel,
        auto_routed=ticket.auto_routed,
        escalated_at=ticket.escalated_at,
        first_response_at=ticket.first_response_at,
        resolution_summary=ticket.resolution_summary,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
    )


def _message_response(message: Message) -> MessageResponse:
    return MessageResponse(
        id=message.id,
        ticket_id=message.ticket_id,
        sender_id=message.sender_id,
        sender_name=message.sender.full_name if message.sender else None,
        message_body=message.message_body,
        is_internal=message.is_internal,
        created_at=message.created_at,
    )


# ---------------------------------------------------------------------------
# Access control
# ---------------------------------------------------------------------------
def can_view(ticket: Ticket, user: User) -> bool:
    if user.role == "admin":
        return True
    if user.role == "student":
        return ticket.student_id == user.id
    if user.role == "staff":
        return ticket.assigned_to == user.id
    if user.role == "hod":
        return user.department_id is not None and ticket.department_id == user.department_id
    return False


def _forbidden() -> AppError:
    return AppError("You do not have permission for this ticket", 403, code="forbidden")


def get_accessible_ticket(db: Session, ticket_id: int, user: User) -> Ticket:
    """Load a ticket only if this user may see it (404 hides existence)."""
    ticket = db.get(Ticket, ticket_id)
    if ticket is None or not can_view(ticket, user):
        # A 404 (rather than 403) prevents ID guessing from confirming existence.
        raise NotFoundError("Ticket")
    return ticket


def _require_assign_perm(ticket: Ticket, user: User) -> None:
    if user.role == "admin":
        return
    if user.role == "hod" and user.department_id is not None and ticket.department_id == user.department_id:
        return
    raise _forbidden()


def _require_status_perm(ticket: Ticket, user: User) -> None:
    if user.role in {"admin", "hod"} and can_view(ticket, user):
        return
    if user.role == "staff" and ticket.assigned_to == user.id:
        return
    raise _forbidden()


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
def create_ticket(db: Session, payload: TicketCreate, student: User) -> TicketResponse:
    should_route = payload.auto_route or payload.department_id is None
    matched_keywords = ""
    if should_route:
        resolved = resolve_department(
            db,
            subject=payload.subject,
            description=payload.description,
            category=payload.category,
        )
        if resolved is None:
            raise AppError(
                "No active department matched this request",
                400,
                code="routing_unresolved",
            )
        department, matched_keywords = resolved
        category = payload.category or (matched_keywords.split(",")[0] or department.name)
    else:
        department = db.get(Department, payload.department_id)
        if department is None or not department.is_active:
            raise NotFoundError("Department")
        category = payload.category

    ticket: Ticket | None = None
    for _ in range(5):
        candidate = Ticket(
            public_reference=_public_reference(),
            subject=payload.subject,
            description=payload.description,
            category=category,
            priority=payload.priority.value,
            status=TicketStatus.NEW.value,
            student_id=student.id,
            department_id=department.id,
            channel=payload.channel,
            auto_routed=should_route,
        )
        db.add(candidate)
        try:
            db.flush()
            ticket = candidate
            break
        except IntegrityError:
            db.rollback()  # only a public_reference collision is realistic here
    if ticket is None:
        raise AppError("Could not generate a unique ticket reference", 500, code="reference_failed")

    db.add(
        TicketStatusHistory(
            ticket_id=ticket.id,
            from_status=None,
            to_status=TicketStatus.NEW.value,
            changed_by_id=student.id,
            note="Ticket submitted",
        )
    )
    record_audit(
        db,
        actor=student,
        action="ticket.created",
        entity_type="ticket",
        entity_id=ticket.id,
        details={"public_reference": ticket.public_reference, "department_id": department.id},
        is_override=False,
    )
    if should_route:
        record_audit(
            db,
            actor=student,
            action="ticket.auto_routed",
            entity_type="ticket",
            entity_id=ticket.id,
            details={
                "public_reference": ticket.public_reference,
                "department_id": department.id,
                "keywords": matched_keywords,
            },
            is_override=False,
        )

    department_staff = db.scalars(
        select(User).where(
            User.is_active.is_(True),
            or_(
                User.role == "admin",
                User.role.in_(("staff", "hod")),
            ),
            or_(User.department_id == department.id, User.role == "admin"),
        )
    ).all()
    notify_ticket_event(
        db,
        ticket=ticket,
        event_type=TICKET_CREATED,
        recipients=list(department_staff),
        subject=f"New ticket {ticket.public_reference}",
        actor=student,
    )

    db.commit()
    db.refresh(ticket)
    return _ticket_response(ticket)


def list_tickets(
    db: Session,
    user: User,
    *,
    skip: int,
    limit: int,
    status: TicketStatus | None = None,
    priority: TicketPriority | None = None,
    department_id: int | None = None,
    assignee_id: int | None = None,
    escalated: bool | None = None,
    search: str | None = None,
) -> TicketListResponse:
    conditions: list[Any] = []
    if user.role == "student":
        conditions.append(Ticket.student_id == user.id)
    elif user.role == "staff":
        conditions.append(Ticket.assigned_to == user.id)
    elif user.role == "hod":
        if user.department_id is None:
            return TicketListResponse(items=[], total=0, skip=skip, limit=limit)
        conditions.append(Ticket.department_id == user.department_id)
    # admin sees all tickets

    if status is not None:
        conditions.append(Ticket.status == status.value)
    if priority is not None:
        conditions.append(Ticket.priority == priority.value)
    if department_id is not None:
        conditions.append(Ticket.department_id == department_id)
    if assignee_id is not None:
        conditions.append(Ticket.assigned_to == assignee_id)
    if escalated is not None:
        conditions.append(Ticket.is_escalated.is_(escalated))
    if search:
        pattern = f"%{search.strip()}%"
        conditions.append(Ticket.subject.ilike(pattern) | Ticket.description.ilike(pattern))

    total = db.scalar(select(func.count(Ticket.id)).where(*conditions)) or 0
    tickets = db.scalars(
        select(Ticket)
        .where(*conditions)
        .order_by(Ticket.created_at.desc(), Ticket.id.desc())
        .offset(skip)
        .limit(limit)
    ).all()
    return TicketListResponse(
        items=[_ticket_response(ticket) for ticket in tickets],
        total=total,
        skip=skip,
        limit=limit,
    )


def get_ticket_detail(db: Session, ticket_id: int, user: User) -> TicketResponse:
    return _ticket_response(get_accessible_ticket(db, ticket_id, user))


def get_ticket_history(db: Session, ticket_id: int, user: User) -> TicketHistoryResponse:
    ticket = get_accessible_ticket(db, ticket_id, user)
    statuses = db.scalars(
        select(TicketStatusHistory)
        .where(TicketStatusHistory.ticket_id == ticket.id)
        .order_by(TicketStatusHistory.created_at, TicketStatusHistory.id)
    ).all()
    assignments = db.scalars(
        select(TicketAssignmentHistory)
        .where(TicketAssignmentHistory.ticket_id == ticket.id)
        .order_by(TicketAssignmentHistory.created_at, TicketAssignmentHistory.id)
    ).all()
    return TicketHistoryResponse(
        status_changes=[StatusHistoryResponse.model_validate(row) for row in statuses],
        assignments=[AssignmentHistoryResponse.model_validate(row) for row in assignments],
    )


def update_ticket(db: Session, ticket_id: int, payload: TicketUpdate, user: User) -> MutationResponse:
    ticket = get_accessible_ticket(db, ticket_id, user)
    supplied = payload.model_dump(exclude_unset=True)

    if user.role == "student":
        raise _forbidden()
    if user.role == "staff" and any(key not in {"status", "resolution_summary"} for key in supplied):
        raise _forbidden()
    if user.role == "hod" and any(
        key not in {"status", "priority", "is_escalated", "resolution_summary"} for key in supplied
    ):
        raise _forbidden()
    _require_status_perm(ticket, user)

    changes: dict[str, Any] = {}
    override_note = "Administrative override" if user.role in {"hod", "admin"} else None

    for field in ("subject", "description", "priority", "is_escalated", "department_id"):
        value = supplied.get(field)
        if value is None:
            continue
        if getattr(ticket, field) != value:
            setattr(ticket, field, value.value if hasattr(value, "value") else value)
            changes[field] = value.value if hasattr(value, "value") else value

    if "department_id" in changes:
        new_department = db.get(Department, changes["department_id"])
        if new_department is None:
            raise NotFoundError("Department")

    status_event: str | None = None
    if payload.status is not None and payload.status.value != ticket.status:
        current = TicketStatus(ticket.status)
        target = payload.status
        if target not in STATUS_TRANSITIONS.get(current, set()):
            raise AppError(
                f"Cannot change status from {current.value} to {target.value}",
                409,
                code="invalid_status_transition",
            )
        if user.role == "staff" and target not in STAFF_ALLOWED_TRANSITIONS:
            raise _forbidden()
        if target.value in ("resolved", "closed"):
            candidate_summary = (supplied.get("resolution_summary") or "").strip() or (
                ticket.resolution_summary or ""
            ).strip()
            if not candidate_summary:
                # Validate before any mutation: AppError does not trigger the
                # DB dependency's rollback, so the session must stay clean.
                raise AppError(
                    "A resolution summary is required before resolving or closing a ticket",
                    400,
                    code="resolution_summary_required",
                )
            status_event = TICKET_RESOLVED if target.value == "resolved" else TICKET_CLOSED

        previous = ticket.status
        ticket.status = target.value
        db.add(
            TicketStatusHistory(
                ticket_id=ticket.id,
                from_status=previous,
                to_status=target.value,
                changed_by_id=user.id,
                note=override_note,
            )
        )
        record_audit(
            db,
            actor=user,
            action="ticket.status_changed",
            entity_type="ticket",
            entity_id=ticket.id,
            details={"from": previous, "to": target.value},
        )
        changes["status"] = target.value

    supplied_summary = supplied.get("resolution_summary")
    if supplied_summary is not None and ticket.resolution_summary != supplied_summary:
        ticket.resolution_summary = supplied_summary
        changes["resolution_summary"] = supplied_summary

    if changes.get("is_escalated") is True:
        if ticket.escalated_at is None:
            ticket.escalated_at = utc_now()
        record_audit(
            db,
            actor=user,
            action="ticket.escalated",
            entity_type="ticket",
            entity_id=ticket.id,
            details={"public_reference": ticket.public_reference},
        )
    if any(key != "status" for key in changes):
        record_audit(
            db,
            actor=user,
            action="ticket.updated",
            entity_type="ticket",
            entity_id=ticket.id,
            details={"fields": [key for key in changes if key != "status"]},
        )

    if not changes:
        raise AppError("No changes supplied", 400, code="empty_update")

    if status_event is not None:
        student = db.get(User, ticket.student_id)
        if student is not None:
            notify_ticket_event(
                db,
                ticket=ticket,
                event_type=status_event,
                recipients=[student],
                subject=(
                    f"Resolved ticket {ticket.public_reference}"
                    if status_event == TICKET_RESOLVED
                    else f"Closed ticket {ticket.public_reference}"
                ),
                actor=user,
                resolution_summary=ticket.resolution_summary,
            )

    db.commit()
    db.refresh(ticket)
    return MutationResponse(ticket=_ticket_response(ticket))


def assign_ticket(db: Session, ticket_id: int, assignee_id: int | None, user: User) -> MutationResponse:
    ticket = get_accessible_ticket(db, ticket_id, user)
    _require_assign_perm(ticket, user)

    if assignee_id is not None:
        assignee = db.get(User, assignee_id)
        if assignee is None or not assignee.is_active:
            raise NotFoundError("Assignee")
        if assignee.role not in ASSIGNABLE_ROLES:
            raise AppError("Tickets can only be assigned to staff, HOD or admin users", 400, code="invalid_assignee")
        if user.role == "hod" and assignee.department_id != user.department_id:
            raise AppError("HOD users may only assign within their department", 403, code="forbidden")

    previous_assignee = ticket.assigned_to
    ticket.assigned_to = assignee_id
    db.add(
        TicketAssignmentHistory(
            ticket_id=ticket.id,
            from_assignee_id=previous_assignee,
            to_assignee_id=assignee_id,
            changed_by_id=user.id,
        )
    )

    # Assignment drives the first workflow step; unassignment returns NEW.
    if assignee_id is not None and ticket.status == TicketStatus.NEW.value:
        ticket.status = TicketStatus.ASSIGNED.value
        db.add(
            TicketStatusHistory(
                ticket_id=ticket.id,
                from_status=TicketStatus.NEW.value,
                to_status=TicketStatus.ASSIGNED.value,
                changed_by_id=user.id,
                note="Automatically assigned",
            )
        )
    elif assignee_id is None and ticket.status == TicketStatus.ASSIGNED.value:
        ticket.status = TicketStatus.NEW.value
        db.add(
            TicketStatusHistory(
                ticket_id=ticket.id,
                from_status=TicketStatus.ASSIGNED.value,
                to_status=TicketStatus.NEW.value,
                changed_by_id=user.id,
                note="Automatically unassigned",
            )
        )

    record_audit(
        db,
        actor=user,
        action="ticket.assigned",
        entity_type="ticket",
        entity_id=ticket.id,
        details={"from_assignee_id": previous_assignee, "to_assignee_id": assignee_id},
    )

    if assignee_id is not None:
        notify_ticket_event(
            db,
            ticket=ticket,
            event_type=TICKET_ASSIGNED,
            recipients=[assignee],
            subject=f"Ticket assigned {ticket.public_reference}",
            actor=user,
        )

        # An assignee on approved leave publishes a public auto-reply message.
        reply_text: str | None = None
        if active_auto_reply is not None:
            try:
                raw_reply = active_auto_reply(db, assignee.id)
                if isinstance(raw_reply, str):
                    reply_text = raw_reply.strip()
                elif isinstance(raw_reply, dict):
                    reply_text = str(raw_reply.get("auto_reply") or "").strip() or None
                else:
                    reply_text = (getattr(raw_reply, "auto_reply", None) or "").strip() or None
            except Exception:  # leave lookup must never fail an assignment
                reply_text = None
        if reply_text:
            auto_message = Message(
                ticket_id=ticket.id,
                sender_id=assignee.id,
                message_body=reply_text,
                is_internal=False,
            )
            db.add(auto_message)
            db.flush()
            record_audit(
                db,
                actor=assignee,
                action="message.created",
                entity_type="ticket",
                entity_id=ticket.id,
                details={
                    "message_id": auto_message.id,
                    "is_internal": False,
                    "auto_reply": True,
                },
            )
            student = db.get(User, ticket.student_id)
            if student is not None:
                notify_ticket_event(
                    db,
                    ticket=ticket,
                    event_type=AUTO_REPLY,
                    recipients=[student],
                    subject=f"Automatic reply for {ticket.public_reference}",
                    public_message=reply_text,
                )

    db.commit()
    db.refresh(ticket)
    return MutationResponse(
        ticket=_ticket_response(ticket),
        message="Assignment updated" if assignee_id else "Ticket unassigned",
    )


def create_message(
    db: Session,
    ticket_id: int,
    payload: MessageCreate,
    sender: User,
    *,
    commit: bool = True,
) -> MessageResponse:
    ticket = get_accessible_ticket(db, ticket_id, sender)
    if payload.is_internal and sender.role == "student":
        raise _forbidden()
    if ticket.status == TicketStatus.CLOSED.value:
        raise AppError("Closed tickets do not accept new messages", 409, code="ticket_closed")

    message = Message(
        ticket_id=ticket.id,
        sender_id=sender.id,
        message_body=payload.message_body,
        is_internal=payload.is_internal,
    )
    db.add(message)
    db.flush()
    record_audit(
        db,
        actor=sender,
        action="message.created",
        entity_type="ticket",
        entity_id=ticket.id,
        details={"message_id": message.id, "is_internal": payload.is_internal},
    )

    if not payload.is_internal:
        # The first staff/HOD/admin public reply starts the response clock.
        if sender.role in ASSIGNABLE_ROLES and ticket.first_response_at is None:
            ticket.first_response_at = utc_now()

        participants: list[User] = []
        student = db.get(User, ticket.student_id)
        if student is not None:
            participants.append(student)
        if ticket.assigned_to is not None:
            assignee = db.get(User, ticket.assigned_to)
            if assignee is not None:
                participants.append(assignee)
        participants = [user for user in participants if user.id != sender.id]

        if participants:
            notify_ticket_event(
                db,
                ticket=ticket,
                event_type=PUBLIC_REPLY,
                recipients=participants,
                subject=f"New reply on {ticket.public_reference}",
                actor=sender,
                public_message=payload.message_body,
            )

    if commit:
        db.commit()
        db.refresh(message)
    return _message_response(message)


def list_messages(db: Session, ticket_id: int, user: User) -> MessageListResponse:
    ticket = get_accessible_ticket(db, ticket_id, user)
    query = select(Message).where(Message.ticket_id == ticket.id)
    if user.role == "student":
        query = query.where(Message.is_internal.is_(False))
    messages = db.scalars(query.order_by(Message.created_at, Message.id)).all()
    return MessageListResponse(items=[_message_response(message) for message in messages], total=len(messages))


def list_assignable_users(db: Session, user: User) -> AssignableUserListResponse:
    """Staff/HOD/admin choices for assignment, scoped for HOD to their department."""
    conditions = [User.is_active.is_(True), User.role.in_(ASSIGNABLE_ROLES)]
    if user.role == "hod":
        if user.department_id is None:
            return AssignableUserListResponse(items=[])
        conditions.append(User.department_id == user.department_id)
    elif user.role not in {"admin", "hod", "staff"}:
        raise _forbidden()

    rows = db.scalars(select(User).where(*conditions).order_by(User.full_name)).all()
    return AssignableUserListResponse(items=[AssignableUserResponse.model_validate(row) for row in rows])


# ---------------------------------------------------------------------------
# Departments (needed by the ticket intake form; admin can maintain them)
# ---------------------------------------------------------------------------
def list_departments(db: Session) -> DepartmentListResponse:
    rows = db.scalars(select(Department).where(Department.is_active.is_(True)).order_by(Department.name)).all()
    return DepartmentListResponse(items=[DepartmentResponse.model_validate(row) for row in rows])


def create_department(db: Session, payload: DepartmentCreate, actor: User) -> DepartmentResponse:
    if db.scalar(select(Department.id).where(func.lower(Department.name) == payload.name.lower())):
        raise AppError("A department with that name already exists", 409, code="duplicate_department")
    department = Department(name=payload.name, description=payload.description, is_active=True)
    db.add(department)
    db.flush()
    record_audit(
        db,
        actor=actor,
        action="department.created",
        entity_type="department",
        entity_id=department.id,
        details={"name": department.name},
    )
    db.commit()
    db.refresh(department)
    return DepartmentResponse.model_validate(department)


def update_department(db: Session, department_id: int, payload: DepartmentUpdate, actor: User) -> DepartmentResponse:
    department = db.get(Department, department_id)
    if department is None:
        raise NotFoundError("Department")
    supplied = payload.model_dump(exclude_unset=True)
    for field in ("name", "description", "is_active"):
        if field in supplied and supplied[field] is not None:
            setattr(department, field, supplied[field])
    if not supplied:
        raise AppError("No changes supplied", 400, code="empty_update")
    record_audit(
        db,
        actor=actor,
        action="department.updated",
        entity_type="department",
        entity_id=department.id,
        details={"fields": sorted(supplied)},
    )
    db.commit()
    db.refresh(department)
    return DepartmentResponse.model_validate(department)
