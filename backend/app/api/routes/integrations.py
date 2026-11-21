"""Inbound intake adapters and non-sensitive integration status flags."""

import hmac

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError, NotFoundError
from app.db.dependencies import get_db
from app.models import User
from app.schemas.integrations import (
    EmailInboundRequest,
    IntegrationStatusResponse,
    WhatsAppInboundRequest,
)
from app.schemas.ticket import TicketCreate
from app.services import email as email_service
from app.services import whatsapp as whatsapp_service
from app.services.tickets import create_ticket

router = APIRouter(prefix="/integrations", tags=["integrations"])


def _require_intake_token(x_intake_token: str) -> None:
    configured = settings.INTAKE_WEBHOOK_TOKEN or ""
    # Fail closed: an unconfigured token must reject every inbound request.
    if not configured or not x_intake_token or not hmac.compare_digest(configured, x_intake_token):
        raise AppError("Invalid intake token", 401, code="invalid_intake_token")


def _resolve_student(db: Session, student_email: str) -> User:
    student = db.scalar(
        select(User).where(func.lower(User.email) == student_email.strip().lower())
    )
    if student is None:
        raise NotFoundError("Student")
    return student


@router.get("/whatsapp/webhook", response_class=PlainTextResponse)
def whatsapp_webhook_verify(
    mode: str | None = Query(default=None, alias="hub.mode"),
    challenge: str | None = Query(default=None, alias="hub.challenge"),
    verify_token: str | None = Query(default=None, alias="hub.verify_token"),
) -> PlainTextResponse:
    """Meta's GET verification handshake. Fails closed when token is unconfigured."""
    configured = settings.WHATSAPP_VERIFY_TOKEN or ""
    if (
        not configured
        or mode != "subscribe"
        or not verify_token
        or not hmac.compare_digest(configured, verify_token)
    ):
        raise AppError("Invalid WhatsApp verification request", 401, code="invalid_verify_token")
    return PlainTextResponse(challenge or "", status_code=200)


@router.get("/status", response_model=IntegrationStatusResponse)
def integration_status() -> IntegrationStatusResponse:
    return IntegrationStatusResponse(
        smtp=email_service.is_configured(),
        whatsapp=whatsapp_service.is_configured(),
        google_oauth=bool(settings.GOOGLE_OAUTH_ENABLED and settings.GOOGLE_OAUTH_CLIENT_ID),
        intake_webhook=bool(settings.INTAKE_WEBHOOK_TOKEN),
    )


@router.post("/email/inbound", response_model=dict)
def email_inbound(
    payload: EmailInboundRequest,
    db: Session = Depends(get_db),
    x_intake_token: str = Header(default="", alias="X-Intake-Token"),
) -> dict:
    _require_intake_token(x_intake_token)
    student = _resolve_student(db, payload.student_email)
    ticket = create_ticket(
        db,
        TicketCreate(
            subject=payload.subject,
            description=payload.body,
            department_id=payload.department_id,
            auto_route=payload.auto_route,
            channel="email",
        ),
        student,
    )
    return {"success": True, "ticket": ticket.model_dump(mode="json")}


@router.post("/whatsapp/inbound", response_model=dict)
def whatsapp_inbound(
    payload: WhatsAppInboundRequest,
    db: Session = Depends(get_db),
    x_intake_token: str = Header(default="", alias="X-Intake-Token"),
) -> dict:
    _require_intake_token(x_intake_token)
    student = _resolve_student(db, payload.student_email)
    subject = f"WhatsApp query: {payload.body[:70]}"
    ticket = create_ticket(
        db,
        TicketCreate(
            subject=subject,
            description=payload.body,
            department_id=payload.department_id,
            auto_route=payload.auto_route,
            channel="whatsapp",
        ),
        student,
    )
    return {"success": True, "ticket": ticket.model_dump(mode="json")}
