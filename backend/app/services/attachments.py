"""Safe ticket-attachment storage outside the database and web root.

Ticket operations never depend on this module being importable in a reduced
deployment; the route imports it explicitly so a missing optional dependency
cannot break core ticket workflows.
"""

from __future__ import annotations

import hashlib
import secrets
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError
from app.models import MessageAttachment, User
from app.schemas.ticket import AttachmentListResponse, AttachmentResponse
from app.services.audit import record_audit
from app.services.malware_scan import scan_attachment_bytes
from app.services.tickets import create_message, get_accessible_ticket, list_messages

_EXPECTED_MIME = {
    "pdf": "application/pdf",
    "txt": "text/plain",
    "md": "text/markdown",
}


def _allowed_types() -> set[str]:
    configured = settings.ALLOWED_UPLOAD_TYPES
    if isinstance(configured, str):
        return {part.strip().lower() for part in configured.split(",") if part.strip()}
    return {str(part).strip().lower() for part in configured}


def _storage_root() -> Path:
    configured = (settings.ATTACHMENT_STORAGE_DIR or "").strip()
    path = Path(configured).expanduser() if configured else Path.cwd() / "var" / "attachments"
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.resolve()


def _validate(upload: UploadFile, data: bytes) -> str:
    filename = (upload.filename or "").strip()
    suffix = Path(filename).suffix.lower().lstrip(".")
    allowed = _allowed_types()
    if suffix not in allowed or suffix not in _EXPECTED_MIME:
        raise AppError(
            f"Attachment type is not allowed. Permitted types: {', '.join(sorted(allowed))}",
            415,
            code="upload_type_not_allowed",
        )
    if len(data) > int(settings.MAX_UPLOAD_BYTES):
        raise AppError("Uploaded attachment is too large", 413, code="upload_too_large")
    if not data:
        raise AppError("Uploaded attachment is empty", 422, code="upload_empty")

    declared = (upload.content_type or "").split(";", 1)[0].strip().lower()
    if declared and declared not in {_EXPECTED_MIME[suffix], "application/octet-stream"}:
        raise AppError("Attachment content type does not match its extension", 415, code="upload_type_mismatch")

    if suffix == "pdf" and not data.startswith(b"%PDF"):
        raise AppError("Attachment is not a valid PDF", 415, code="upload_invalid_pdf")
    if suffix in {"txt", "md"}:
        try:
            data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise AppError("Text attachments must be UTF-8 encoded", 415, code="upload_invalid_text") from exc
    return suffix


def _safe_file_name(original: str, suffix: str) -> str:
    return f"{secrets.token_hex(16)}.{suffix}"


def create_message_attachment(
    db: Session,
    ticket_id: int,
    sender: User,
    upload: UploadFile,
    *,
    message_body: str | None = None,
    is_internal: bool = False,
) -> AttachmentResponse:
    """Store bytes safely, then create a message and audited attachment row."""
    ticket = get_accessible_ticket(db, ticket_id, sender)
    if is_internal and sender.role == "student":
        raise AppError("Students cannot create internal notes", 403, code="forbidden")

    data = upload.file.read(int(settings.MAX_UPLOAD_BYTES) + 1)
    suffix = _validate(upload, data)
    original_name = (upload.filename or "attachment").strip()[:255]
    try:
        scan_attachment_bytes(data, original_name)
    except AppError:
        raise
    except Exception as exc:
        raise AppError(
            "Malware scanner is unavailable",
            503,
            code="attachment_scan_unavailable",
        ) from exc
    stored_name = _safe_file_name(original_name, suffix)
    relative_path = Path(str(ticket.id)) / stored_name
    destination = _storage_root() / relative_path
    destination.parent.mkdir(parents=True, exist_ok=True)

    checksum = hashlib.sha256(data).hexdigest()
    # Write atomically so interrupted uploads never leave a partial file.
    temporary = destination.with_suffix(destination.suffix + ".part")
    temporary.write_bytes(data)
    temporary.replace(destination)

    try:
        message = create_message(
            db,
            ticket_id,
            _attachment_message_payload(message_body, original_name, is_internal),
            sender,
            commit=False,
        )
        attachment = MessageAttachment(
            message_id=message.id,
            file_name=original_name,
            content_type=upload.content_type or _EXPECTED_MIME[suffix],
            size_bytes=len(data),
            storage_path=str(relative_path).replace("\\", "/"),
            checksum=checksum,
        )
        db.add(attachment)
        db.flush()
        record_audit(
            db,
            actor=sender,
            action="attachment.uploaded",
            entity_type="ticket",
            entity_id=ticket.id,
            details={
                "message_id": message.id,
                "attachment_id": attachment.id,
                "file_name": original_name,
                "size_bytes": len(data),
                "is_internal": is_internal,
            },
        )
        db.commit()
    except Exception:
        db.rollback()
        destination.unlink(missing_ok=True)
        raise

    return AttachmentResponse(
        id=attachment.id,
        message_id=attachment.message_id,
        file_name=attachment.file_name,
        content_type=attachment.content_type,
        size_bytes=attachment.size_bytes,
        created_at=attachment.created_at,
    )


def _attachment_message_payload(message_body: str | None, file_name: str, is_internal: bool):
    # Imported lazily to keep this optional module independent of schema imports
    # at application startup.
    from app.schemas.ticket import MessageCreate

    body = (message_body or "").strip() or f"Attachment: {file_name}"
    return MessageCreate(message_body=body, is_internal=is_internal)


def list_ticket_attachments(db: Session, ticket_id: int, user: User) -> AttachmentListResponse:
    """Return attachment metadata for tickets the caller may already view."""
    get_accessible_ticket(db, ticket_id, user)
    visible_message_ids = [row.id for row in list_messages(db, ticket_id, user).items]
    if not visible_message_ids:
        return AttachmentListResponse(items=[], total=0)
    rows = db.scalars(
        select(MessageAttachment)
        .where(MessageAttachment.message_id.in_(visible_message_ids))
        .order_by(MessageAttachment.created_at, MessageAttachment.id)
    ).all()
    items = [
        AttachmentResponse(
            id=row.id,
            message_id=row.message_id,
            file_name=row.file_name,
            content_type=row.content_type,
            size_bytes=row.size_bytes,
            created_at=row.created_at,
        )
        for row in rows
    ]
    return AttachmentListResponse(items=items, total=len(items))
