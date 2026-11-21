"""Deterministic tests for governed knowledge upload, lifecycle and retrieval."""

from __future__ import annotations

import hashlib
from collections.abc import Iterator

import pytest
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from sqlalchemy import select
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routes.knowledge import router as knowledge_router
from app.core.config import settings
from app.core.errors import AppError, error_response
from app.core.security import create_access_token
from app.db.dependencies import get_db
from app.models import AuditLog, KnowledgeDocument, User
from app.schemas.knowledge import KnowledgeUpdate
from app.services.knowledge import (
    approve_knowledge_document,
    create_knowledge_document,
    deactivate_knowledge_document,
    get_database_knowledge_repository,
)
from app.agents.tools.knowledge_search import DatabaseKnowledgeRepository


API = f"{settings.API_V1_PREFIX}/knowledge"


@pytest.fixture()
def knowledge_client(db_session) -> Iterator[TestClient]:
    """Mount only the knowledge router with the project's error contract."""
    app = FastAPI()
    app.include_router(knowledge_router, prefix=settings.API_V1_PREFIX)

    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError):
        return error_response(
            status_code=exc.status_code, error=exc.message, detail=exc.detail, code=exc.code
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, exc: RequestValidationError):
        return error_response(
            status_code=422, error="Validation error", detail=exc.errors(), code="validation_error"
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(_: Request, exc: StarletteHTTPException):
        return error_response(status_code=exc.status_code, error=str(exc.detail))

    def override_get_db() -> Iterator:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client


def _auth(user: User) -> dict[str, str]:
    token, _ = create_access_token(user.id, user.role)
    return {"Authorization": f"Bearer {token}"}


def _minimal_pdf(text: str) -> bytes:
    """Build a small, valid single-page PDF with a correct xref table."""
    stream = f"BT /F1 14 Tf 72 700 Td ({text}) Tj ET".encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(stream)} >>\nstream\n".encode("ascii") + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets: list[int] = []
    for index, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{index} 0 obj\n".encode("ascii")
        out += body + b"\nendobj\n"
    xref_position = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode("ascii")
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode("ascii")
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_position}\n%%EOF\n"
    ).encode("ascii")
    return bytes(out)


def _audit_actions(db_session, action: str) -> list[AuditLog]:
    return list(
        db_session.scalars(select(AuditLog).where(AuditLog.action == action)).all()
    )


def test_text_upload_creates_unapproved_version_and_audit(knowledge_client, db_session, users):
    content = "To reset your password, use the student portal."
    response = knowledge_client.post(
        API,
        headers=_auth(users["admin"]),
        data={
            "title": "Password policy",
            "source_type": "text",
            "source_key": "faq-passwords",
            "content": content,
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["version"] == 1
    assert body["source_key"] == "faq-passwords"
    assert body["source_type"] == "text"
    assert body["content_text"] == content
    assert body["checksum"] == hashlib.sha256(content.encode("utf-8")).hexdigest()
    assert body["is_approved"] is False
    assert body["is_active"] is True
    assert body["uploader_name"] == users["admin"].full_name
    assert not any("path" in key.lower() for key in body)

    row = db_session.get(KnowledgeDocument, body["id"])
    assert row.uploaded_by_id == users["admin"].id
    audits = _audit_actions(db_session, "knowledge.document_uploaded")
    assert len(audits) == 1
    assert audits[0].entity_id == str(body["id"])
    assert audits[0].actor_id == users["admin"].id


def test_pdf_upload_is_parsed_with_pypdf(knowledge_client, db_session, users):
    pdf_bytes = _minimal_pdf("PDF POLICY CONTENT ALPHA")
    response = knowledge_client.post(
        API,
        headers=_auth(users["admin"]),
        data={"title": "PDF policy", "source_type": "pdf", "source_key": "policy-pdf"},
        files={"file": ("policy.pdf", pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["source_type"] == "pdf"
    assert body["file_name"] == "policy.pdf"
    assert "PDF POLICY CONTENT ALPHA" in body["content_text"]
    assert body["checksum"] == hashlib.sha256(pdf_bytes).hexdigest()


def test_version_increments_per_source_key_and_versions_endpoint(
    knowledge_client, users
):
    for index in (1, 2):
        response = knowledge_client.post(
            API,
            headers=_auth(users["admin"]),
            data={
                "title": f"Portal policy v{index}",
                "source_type": "text",
                "source_key": "portal-policy",
                "content": f"Portal version {index} guidance.",
            },
        )
        assert response.status_code == 201, response.text
        assert response.json()["version"] == index
        document_id = response.json()["id"]

    versions = knowledge_client.get(
        f"{API}/{document_id}/versions", headers=_auth(users["admin"])
    )
    assert versions.status_code == 200, versions.text
    payload = versions.json()
    assert payload["source_key"] == "portal-policy"
    assert [item["version"] for item in payload["items"]] == [1, 2]
    assert len({item["checksum"] for item in payload["items"]}) == 2


def test_approval_and_deactivation_are_audited(knowledge_client, db_session, users):
    created = knowledge_client.post(
        API,
        headers=_auth(users["admin"]),
        data={
            "title": "Leave rules",
            "source_type": "text",
            "source_key": "leave-rules",
            "content": "Leave requests are submitted two weeks in advance.",
        },
    )
    document_id = created.json()["id"]

    approved = knowledge_client.patch(
        f"{API}/{document_id}", headers=_auth(users["admin"]), json={"is_approved": True}
    )
    assert approved.status_code == 200, approved.text
    approved_body = approved.json()
    assert approved_body["is_approved"] is True
    assert approved_body["approved_by_id"] == users["admin"].id
    assert approved_body["approver_name"] == users["admin"].full_name
    assert approved_body["approved_at"] is not None
    assert len(_audit_actions(db_session, "knowledge.document_approved")) == 1

    deleted = knowledge_client.delete(f"{API}/{document_id}", headers=_auth(users["admin"]))
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["is_active"] is False
    assert len(_audit_actions(db_session, "knowledge.document_deactivated")) == 1
    # Soft delete only: the row is still addressable for audit/history.
    assert knowledge_client.get(f"{API}/{document_id}", headers=_auth(users["admin"])).status_code == 200


def test_hod_department_scoping_for_management(knowledge_client, db_session, users, departments):
    registry_id = departments["registry"].id
    other_id = departments["other"].id

    own = knowledge_client.post(
        API,
        headers=_auth(users["hod"]),
        data={
            "title": "Registry guidance",
            "source_type": "text",
            "source_key": "registry-guidance",
            "content": "Registry guidance for staff.",
            "department_id": str(registry_id),
        },
    )
    assert own.status_code == 201, own.text
    assert own.json()["department_id"] == registry_id

    global_doc = knowledge_client.post(
        API,
        headers=_auth(users["hod"]),
        data={
            "title": "Global guidance",
            "source_type": "text",
            "source_key": "global-guidance",
            "content": "Global guidance for everyone.",
        },
    )
    assert global_doc.status_code == 201, global_doc.text
    assert global_doc.json()["department_id"] is None

    forbidden_create = knowledge_client.post(
        API,
        headers=_auth(users["hod"]),
        data={
            "title": "Other department",
            "source_type": "text",
            "source_key": "other-guidance",
            "content": "Not yours to manage.",
            "department_id": str(other_id),
        },
    )
    assert forbidden_create.status_code == 403, forbidden_create.text

    own_id = own.json()["id"]
    assert knowledge_client.patch(
        f"{API}/{own_id}", headers=_auth(users["hod"]), json={"is_approved": True}
    ).status_code == 200
    assert knowledge_client.patch(
        f"{API}/{own_id}", headers=_auth(users["hod_other"]), json={"is_approved": True}
    ).status_code == 403
    assert knowledge_client.delete(
        f"{API}/{own_id}", headers=_auth(users["hod_other"])
    ).status_code == 403
    assert knowledge_client.get(
        f"{API}/{own_id}", headers=_auth(users["hod_other"])
    ).status_code == 403
    assert knowledge_client.patch(
        f"{API}/{own_id}", headers=_auth(users["admin"]), json={"is_active": False}
    ).status_code == 200


def test_students_and_staff_cannot_manage_and_students_cannot_read(
    knowledge_client, users
):
    payload = {
        "title": "Restricted content",
        "source_type": "text",
        "source_key": "restricted",
        "content": "Only managers may create this.",
    }
    assert knowledge_client.post(API, headers=_auth(users["student"]), data=payload).status_code == 403
    assert knowledge_client.post(API, headers=_auth(users["staff"]), data=payload).status_code == 403
    assert knowledge_client.get(API, headers=_auth(users["student"])).status_code == 403
    assert knowledge_client.get(API, headers=_auth(users["staff"])).status_code == 200


def test_unapproved_document_is_never_retrieved(db_session, users):
    create_knowledge_document(
        db_session,
        user=users["admin"],
        title="Unapproved secret policy",
        source_key="unapproved-secret",
        content="super secret alpha policy for password resets",
    )
    repository = get_database_knowledge_repository(db_session, users["admin"])
    assert repository.search("super secret alpha policy password resets") == []
    assert DatabaseKnowledgeRepository(db_session).search("super secret alpha policy") == []


def test_approved_active_document_is_retrieved_with_citation_and_scope(
    db_session, users, departments
):
    global_doc = create_knowledge_document(
        db_session,
        user=users["admin"],
        title="Approved portal policy",
        source_key="approved-portal",
        content="The student portal password policy requires a reset every ninety days.",
    )
    approve_knowledge_document(db_session, global_doc.id, users["admin"])

    repository = get_database_knowledge_repository(db_session, users["admin"])
    matches = repository.search("student portal password reset policy")
    assert matches
    assert matches[0]["source_id"] == f"kb-{global_doc.id}-v1"
    assert "student portal password policy" in matches[0]["excerpt"].lower()

    registry_id = departments["registry"].id
    scoped = create_knowledge_document(
        db_session,
        user=users["admin"],
        title="Registry password policy",
        source_key="registry-password",
        content="Registry password reset requires a staff verification step.",
        department_id=registry_id,
    )
    approve_knowledge_document(db_session, scoped.id, users["admin"])

    registry_repo = get_database_knowledge_repository(db_session, users["hod"])
    other_repo = get_database_knowledge_repository(db_session, users["hod_other"])
    registry_ids = {item["source_id"] for item in registry_repo.search("password reset", limit=10)}
    other_ids = {item["source_id"] for item in other_repo.search("password reset", limit=10)}
    assert f"kb-{scoped.id}-v1" in registry_ids
    assert f"kb-{scoped.id}-v1" not in other_ids
    assert f"kb-{global_doc.id}-v1" in registry_ids
    assert f"kb-{global_doc.id}-v1" in other_ids


def test_deactivated_document_disappears_from_repository(db_session, users):
    document = create_knowledge_document(
        db_session,
        user=users["admin"],
        title="Temporary policy",
        source_key="temporary-policy",
        content="Temporary university bandwidth policy for campus wifi.",
    )
    approve_knowledge_document(db_session, document.id, users["admin"])
    repository = get_database_knowledge_repository(db_session, users["admin"])
    assert repository.search("university bandwidth policy campus wifi")

    deactivate_knowledge_document(db_session, document.id, users["admin"])
    assert repository.search("university bandwidth policy campus wifi") == []


def test_upload_size_and_type_limits_are_enforced(knowledge_client, users, monkeypatch):
    monkeypatch.setattr(settings, "MAX_UPLOAD_BYTES", 32)
    too_large = knowledge_client.post(
        API,
        headers=_auth(users["admin"]),
        data={
            "title": "Oversized",
            "source_type": "text",
            "source_key": "oversized",
            "content": "x" * 100,
        },
    )
    assert too_large.status_code == 413, too_large.text

    monkeypatch.setattr(settings, "MAX_UPLOAD_BYTES", 1024)
    monkeypatch.setattr(settings, "ALLOWED_UPLOAD_TYPES", "pdf")
    disallowed = knowledge_client.post(
        API,
        headers=_auth(users["admin"]),
        data={"title": "Notes", "source_type": "md", "source_key": "notes"},
        files={"file": ("notes.md", b"# Disallowed markdown", "text/markdown")},
    )
    assert disallowed.status_code == 400, disallowed.text
    assert disallowed.json()["code"] == "unsupported_upload_type"


def test_list_filters_approved_active_department_and_search(knowledge_client, users, departments):
    created = knowledge_client.post(
        API,
        headers=_auth(users["admin"]),
        data={
            "title": "Scholarship eligibility",
            "source_type": "text",
            "source_key": "scholarship-eligibility",
            "content": "Maintain a 3.0 GPA for scholarship eligibility.",
            "department_id": str(departments["scholarships"].id),
        },
    )
    document_id = created.json()["id"]
    knowledge_client.patch(
        f"{API}/{document_id}", headers=_auth(users["admin"]), json={"is_approved": True}
    )

    approved = knowledge_client.get(
        API, headers=_auth(users["admin"]), params={"approved_only": True}
    )
    assert approved.status_code == 200
    assert [item["id"] for item in approved.json()["items"]] == [document_id]

    filtered = knowledge_client.get(
        API,
        headers=_auth(users["admin"]),
        params={"search": "eligibility", "department_id": departments["scholarships"].id},
    )
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1

    wrong_department = knowledge_client.get(
        API,
        headers=_auth(users["admin"]),
        params={"department_id": departments["registry"].id},
    )
    assert wrong_department.json()["total"] == 0

    # HOD admins cannot use the filter to peek into a different department.
    denied = knowledge_client.get(
        API,
        headers=_auth(users["hod"]),
        params={"department_id": departments["other"].id},
    )
    assert denied.status_code == 403


def test_service_update_helper_rejects_non_manager(db_session, users):
    created = create_knowledge_document(
        db_session,
        user=users["admin"],
        title="Manager only",
        source_key="manager-only",
        content="Only an HOD or admin may update this.",
    )
    with pytest.raises(AppError) as caught:
        from app.services.knowledge import update_knowledge_document

        update_knowledge_document(
            db_session, created.id, KnowledgeUpdate(is_approved=True), users["staff"]
        )
    assert caught.value.status_code == 403
