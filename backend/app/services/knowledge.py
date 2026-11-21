"""Governed knowledge-document management and approved-source retrieval.

Management is restricted to HOD/admin users. All writes are audited, versions
are monotonic per ``source_key``, and retrieval only ever sees approved, active
rows through :class:`DatabaseKnowledgeRepository`.
"""

from __future__ import annotations

import hashlib
import io
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from pypdf import PdfReader
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.agents.tools.knowledge_search import DatabaseKnowledgeRepository
from app.core.config import settings
from app.core.enums import UserRole
from app.core.errors import AppError, NotFoundError
from app.models import Department, KnowledgeDocument, User
from app.schemas.knowledge import (
    KnowledgeDocumentResponse,
    KnowledgeListResponse,
    KnowledgeUpdate,
    KnowledgeVersionListResponse,
)
from app.services.audit import record_audit

SOURCE_TYPES = {"text", "txt", "md", "pdf"}
FILE_SOURCE_TYPES = {"txt", "md", "pdf"}
_MIME_TYPES = {
    "txt": "text/plain",
    "md": "text/markdown",
    "pdf": "application/pdf",
    "text": "text/plain",
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _allowed_types() -> set[str]:
    """Parse the configured allow-list; inline text uploads are always valid."""
    configured = settings.ALLOWED_UPLOAD_TYPES
    if isinstance(configured, str):
        values = {part.strip().lower() for part in configured.split(",") if part.strip()}
    else:
        values = {str(part).strip().lower() for part in configured}
    # "text" is inline content, not an uploaded file type; the model supports it.
    return values | {"text"}


def _max_bytes() -> int:
    return int(settings.MAX_UPLOAD_BYTES)


def _too_large() -> AppError:
    return AppError("Uploaded content is too large", 413, code="upload_too_large")


def _assert_manager(user: User) -> None:
    if user.role not in {UserRole.HOD.value, UserRole.ADMIN.value}:
        raise AppError(
            "Knowledge management requires HOD or admin access", 403, code="forbidden"
        )


def _assert_readable(document: KnowledgeDocument, user: User) -> None:
    """Staff+ may read; an HOD cannot read another department's document."""
    if user.role not in {UserRole.STAFF.value, UserRole.HOD.value, UserRole.ADMIN.value}:
        raise AppError("Knowledge access requires staff access", 403, code="forbidden")
    if user.role == UserRole.HOD.value:
        if document.department_id is None:
            return
        if user.department_id is None or document.department_id != user.department_id:
            raise AppError("You do not have permission for this document", 403, code="forbidden")


def _assert_manageable(document: KnowledgeDocument, user: User) -> None:
    _assert_manager(user)
    if user.role == UserRole.ADMIN.value or document.department_id is None:
        return
    if user.department_id is not None and document.department_id == user.department_id:
        return
    raise AppError("You do not have permission for this document", 403, code="forbidden")


def _validate_department(db: Session, user: User, department_id: int | None) -> None:
    _assert_manager(user)
    if department_id is None:
        return  # global document
    if db.get(Department, department_id) is None:
        raise NotFoundError("Department")
    if user.role == UserRole.HOD.value and department_id != user.department_id:
        raise AppError("You do not have permission for this department", 403, code="forbidden")


def _get_document(db: Session, document_id: int) -> KnowledgeDocument:
    document = db.get(KnowledgeDocument, document_id)
    if document is None:
        raise NotFoundError("Knowledge document")
    return document


def _response(db: Session, document: KnowledgeDocument) -> KnowledgeDocumentResponse:
    uploader = db.get(User, document.uploaded_by_id)
    approver = db.get(User, document.approved_by_id) if document.approved_by_id else None
    return KnowledgeDocumentResponse(
        id=document.id,
        title=document.title,
        source_key=document.source_key,
        version=document.version,
        source_type=document.source_type,
        file_name=document.file_name,
        mime_type=document.mime_type,
        checksum=document.checksum,
        content_text=document.content_text,
        department_id=document.department_id,
        uploaded_by_id=document.uploaded_by_id,
        uploader_name=uploader.full_name if uploader else None,
        approved_by_id=document.approved_by_id,
        approver_name=approver.full_name if approver else None,
        approved_at=document.approved_at,
        is_approved=document.is_approved,
        is_active=document.is_active,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


def _default_source_key(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:180] or "document"
    return f"{slug}-{secrets.token_hex(3)}"


def _next_version(db: Session, source_key: str) -> int:
    latest = db.scalar(
        select(func.max(KnowledgeDocument.version)).where(
            KnowledgeDocument.source_key == source_key
        )
    )
    return int(latest or 0) + 1


def _effective_source_type(declared: str | None, file: UploadFile | None) -> str:
    source_type = (declared or "text").strip().lower()
    if source_type not in SOURCE_TYPES:
        raise AppError("Unsupported knowledge source type", 400, code="invalid_source_type")
    if file is None:
        return source_type
    suffix = Path(file.filename or "").suffix.lower().lstrip(".")
    if suffix in FILE_SOURCE_TYPES:
        # The bytes determine how the upload is parsed; never trust a mismatch.
        return suffix
    if source_type == "text":
        raise AppError(
            "File uploads must use txt, md or pdf source types",
            400,
            code="invalid_source_type",
        )
    return source_type


def _read_upload(file: UploadFile) -> bytes:
    limit = _max_bytes()
    raw = file.file.read(limit + 1)
    if len(raw) > limit:
        raise _too_large()
    return raw


def _extract_content(source_type: str, raw: bytes) -> str:
    if source_type == "pdf":
        try:
            reader = PdfReader(io.BytesIO(raw))
            text = "\n\n".join((page.extract_text() or "") for page in reader.pages)
        except Exception as exc:  # pypdf raises several parser-specific errors
            raise AppError("Uploaded PDF could not be parsed", 400, code="invalid_pdf") from exc
        text = text.strip()
        if not text:
            raise AppError("Uploaded PDF has no extractable text", 400, code="empty_document")
        return text

    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:  # pragma: no cover - latin-1 never fails
        text = raw.decode("utf-8", errors="replace")
    if not text.strip():
        raise AppError("Document content cannot be empty", 400, code="empty_document")
    return text


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
def create_knowledge_document(
    db: Session,
    *,
    user: User,
    title: str,
    source_type: str = "text",
    source_key: str | None = None,
    content: str | None = None,
    file: UploadFile | None = None,
    department_id: int | None = None,
) -> KnowledgeDocumentResponse:
    """Create an unapproved version of a knowledge document from text or file."""
    _validate_department(db, user, department_id)
    clean_title = (title or "").strip()
    if not clean_title or len(clean_title) > 255:
        raise AppError("A title of 1-255 characters is required", 400, code="invalid_title")

    effective_type = _effective_source_type(source_type, file)
    if effective_type not in _allowed_types():
        raise AppError("This upload type is not allowed", 400, code="unsupported_upload_type")

    file_name: str | None = None
    mime_type: str | None = None
    if file is not None:
        raw = _read_upload(file)
        # Store only a logical file name, never a client or server path.
        file_name = Path(file.filename or "upload").name[:255]
        mime_type = (file.content_type or _MIME_TYPES.get(effective_type, ""))[:120] or None
    else:
        if effective_type == "pdf":
            raise AppError("A PDF source requires an uploaded file", 400, code="file_required")
        text_content = content or ""
        if not text_content.strip():
            raise AppError("Text content is required", 400, code="empty_document")
        raw = text_content.encode("utf-8")
        if len(raw) > _max_bytes():
            raise _too_large()

    content_text = _extract_content(effective_type, raw)
    checksum = hashlib.sha256(raw).hexdigest()
    key = (source_key or "").strip() or _default_source_key(clean_title)

    document = KnowledgeDocument(
        title=clean_title,
        source_key=key[:255],
        version=_next_version(db, key[:255]),
        source_type=effective_type,
        file_name=file_name,
        mime_type=mime_type,
        checksum=checksum,
        content_text=content_text,
        department_id=department_id,
        uploaded_by_id=user.id,
        is_approved=False,
        is_active=True,
    )
    db.add(document)
    db.flush()
    record_audit(
        db,
        actor=user,
        action="knowledge.document_uploaded",
        entity_type="knowledge_document",
        entity_id=document.id,
        details={
            "source_key": document.source_key,
            "version": document.version,
            "source_type": document.source_type,
            "department_id": department_id,
            "checksum": checksum,
        },
        is_override=False,
    )
    db.commit()
    db.refresh(document)
    return _response(db, document)


def update_knowledge_document(
    db: Session,
    document_id: int,
    payload: KnowledgeUpdate,
    user: User,
) -> KnowledgeDocumentResponse:
    """Apply an authorized PATCH, auditing approval and deactivation changes."""
    document = _get_document(db, document_id)
    _assert_manageable(document, user)

    metadata_changed = False
    if payload.title is not None:
        document.title = payload.title
        metadata_changed = True
    if payload.content_text is not None:
        if not payload.content_text.strip():
            raise AppError("Document content cannot be empty", 400, code="empty_document")
        encoded = payload.content_text.encode("utf-8")
        if len(encoded) > _max_bytes():
            raise _too_large()
        document.content_text = payload.content_text
        document.checksum = hashlib.sha256(encoded).hexdigest()
        metadata_changed = True
    if payload.department_id is not None:
        _validate_department(db, user, payload.department_id)
        document.department_id = payload.department_id
        metadata_changed = True

    if payload.is_approved is not None and payload.is_approved != document.is_approved:
        if payload.is_approved:
            document.is_approved = True
            document.approved_by_id = user.id
            document.approved_at = datetime.now(timezone.utc)
            action = "knowledge.document_approved"
        else:
            document.is_approved = False
            document.approved_by_id = None
            document.approved_at = None
            action = "knowledge.document_unapproved"
        record_audit(
            db,
            actor=user,
            action=action,
            entity_type="knowledge_document",
            entity_id=document.id,
            details={"source_key": document.source_key, "version": document.version},
            is_override=False,
        )

    if payload.is_active is not None and payload.is_active != document.is_active:
        document.is_active = payload.is_active
        action = (
            "knowledge.document_activated"
            if payload.is_active
            else "knowledge.document_deactivated"
        )
        record_audit(
            db,
            actor=user,
            action=action,
            entity_type="knowledge_document",
            entity_id=document.id,
            details={"source_key": document.source_key, "version": document.version},
            is_override=False,
        )

    if metadata_changed:
        record_audit(
            db,
            actor=user,
            action="knowledge.document_updated",
            entity_type="knowledge_document",
            entity_id=document.id,
            details={"source_key": document.source_key, "version": document.version},
            is_override=False,
        )

    db.commit()
    db.refresh(document)
    return _response(db, document)


def approve_knowledge_document(
    db: Session, document_id: int, user: User
) -> KnowledgeDocumentResponse:
    """Explicit approval helper used by callers that do not send a PATCH body."""
    return update_knowledge_document(
        db, document_id, KnowledgeUpdate(is_approved=True), user
    )


def deactivate_knowledge_document(
    db: Session, document_id: int, user: User
) -> KnowledgeDocumentResponse:
    """Soft-delete: deactivated rows remain auditable but are never retrieved."""
    return update_knowledge_document(
        db, document_id, KnowledgeUpdate(is_active=False), user
    )


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------
def list_knowledge_documents(
    db: Session,
    user: User,
    *,
    skip: int = 0,
    limit: int = 20,
    search: str | None = None,
    approved_only: bool = False,
    active_only: bool = False,
    department_id: int | None = None,
) -> KnowledgeListResponse:
    """List documents with role-aware scoping and deterministic pagination."""
    if user.role not in {UserRole.STAFF.value, UserRole.HOD.value, UserRole.ADMIN.value}:
        raise AppError("Knowledge access requires staff access", 403, code="forbidden")
    conditions: list[Any] = []
    if user.role == UserRole.HOD.value:
        if department_id is not None and department_id != user.department_id:
            raise AppError("You do not have permission for this department", 403, code="forbidden")
        conditions.append(
            or_(
                KnowledgeDocument.department_id.is_(None),
                KnowledgeDocument.department_id == user.department_id,
            )
        )
    if department_id is not None:
        conditions.append(KnowledgeDocument.department_id == department_id)
    if approved_only:
        conditions.append(KnowledgeDocument.is_approved.is_(True))
    if active_only:
        conditions.append(KnowledgeDocument.is_active.is_(True))
    if search and search.strip():
        pattern = f"%{search.strip()}%"
        conditions.append(
            or_(
                KnowledgeDocument.title.ilike(pattern),
                KnowledgeDocument.source_key.ilike(pattern),
                KnowledgeDocument.content_text.ilike(pattern),
            )
        )

    total = db.scalar(
        select(func.count()).select_from(KnowledgeDocument).where(*conditions)
    )
    rows = db.scalars(
        select(KnowledgeDocument)
        .where(*conditions)
        .order_by(KnowledgeDocument.created_at.desc(), KnowledgeDocument.id.desc())
        .offset(skip)
        .limit(limit)
    ).all()
    return KnowledgeListResponse(
        items=[_response(db, row) for row in rows],
        total=int(total or 0),
        skip=skip,
        limit=limit,
    )


def get_knowledge_document(
    db: Session, document_id: int, user: User
) -> KnowledgeDocumentResponse:
    document = _get_document(db, document_id)
    _assert_readable(document, user)
    return _response(db, document)


def list_knowledge_versions(
    db: Session,
    user: User,
    *,
    source_key: str | None = None,
    document_id: int | None = None,
) -> KnowledgeVersionListResponse:
    """Return every version of a source key (resolved from a document id)."""
    if document_id is not None:
        document = _get_document(db, document_id)
        _assert_readable(document, user)
        source_key = document.source_key
    if not source_key:
        raise AppError("A source key or document id is required", 400, code="invalid_source_key")

    conditions = [KnowledgeDocument.source_key == source_key]
    if user.role == UserRole.HOD.value:
        conditions.append(
            or_(
                KnowledgeDocument.department_id.is_(None),
                KnowledgeDocument.department_id == user.department_id,
            )
        )
    rows = db.scalars(
        select(KnowledgeDocument)
        .where(*conditions)
        .order_by(KnowledgeDocument.version.asc())
    ).all()
    return KnowledgeVersionListResponse(
        source_key=source_key,
        items=[_response(db, row) for row in rows],
        total=len(rows),
    )


def get_database_knowledge_repository(
    db: Session, user: User | None = None
) -> DatabaseKnowledgeRepository:
    """Factory for the agent service to wire into the research node.

    The repository itself never returns unapproved or deactivated rows. A
    signed-in non-admin is additionally limited to global documents plus
    documents in their own department.
    """
    if user is None or user.role == UserRole.ADMIN.value:
        return DatabaseKnowledgeRepository(db)
    if user.department_id is None:
        return DatabaseKnowledgeRepository(db, global_only=True)
    return DatabaseKnowledgeRepository(db, department_id=user.department_id)


# Short aliases for callers that prefer the concise service names.
create_document = create_knowledge_document
list_documents = list_knowledge_documents
get_document = get_knowledge_document
update_document = update_knowledge_document
approve_document = approve_knowledge_document
deactivate_document = deactivate_knowledge_document
list_versions = list_knowledge_versions
