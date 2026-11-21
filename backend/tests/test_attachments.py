"""Ticket attachment storage, validation, authorization and visibility tests."""

from __future__ import annotations

from sqlalchemy import func, select

from app.core.config import settings
from app.models import AuditLog, Message, MessageAttachment, Notification
from tests.conftest import auth_header

TICKETS_URL = "/api/v1/tickets"


def _create_ticket(client, users, departments) -> int:
    header = auth_header(client, users["student"].email)
    response = client.post(
        TICKETS_URL,
        headers=header,
        json={
            "subject": "Attachment verification request",
            "description": "This description is long enough to create a ticket.",
            "department_id": departments["registry"].id,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _upload(client, ticket_id: int, header: dict[str, str], **kwargs):
    files = kwargs.pop(
        "files",
        {"file": ("notes.txt", b"Plain UTF-8 attachment text.", "text/plain")},
    )
    return client.post(
        f"{TICKETS_URL}/{ticket_id}/attachments",
        headers=header,
        files=files,
        data=kwargs,
    )


def test_student_uploads_attachment_outside_web_root_and_lists_safe_metadata(
    client, db_session, tmp_path, monkeypatch, users, departments
) -> None:
    root = tmp_path / "stored-attachments"
    monkeypatch.setattr(settings, "ATTACHMENT_STORAGE_DIR", str(root))
    ticket_id = _create_ticket(client, users, departments)
    header = auth_header(client, users["student"].email)

    response = _upload(client, ticket_id, header, message_body="Supporting notes")
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["file_name"] == "notes.txt"
    assert body["content_type"] == "text/plain"
    assert body["size_bytes"] == len(b"Plain UTF-8 attachment text.")
    assert "storage_path" not in body and "checksum" not in body

    stored = list(root.rglob("*.txt"))
    assert len(stored) == 1
    assert stored[0].read_bytes() == b"Plain UTF-8 attachment text."

    attachment = db_session.get(MessageAttachment, body["id"])
    assert attachment is not None
    assert attachment.checksum
    assert "/" in attachment.storage_path or "\\" in attachment.storage_path

    listing = client.get(f"{TICKETS_URL}/{ticket_id}/attachments", headers=header)
    assert listing.status_code == 200, listing.text
    assert listing.json()["total"] == 1
    assert listing.json()["items"][0]["message_id"] == body["message_id"]

    message = db_session.get(Message, body["message_id"])
    assert message is not None
    assert message.message_body == "Supporting notes"
    audit = db_session.scalar(
        select(func.count(AuditLog.id)).where(AuditLog.action == "attachment.uploaded")
    )
    assert audit == 1


def test_attachment_type_and_content_validation_rejects_bad_uploads(
    client, db_session, tmp_path, monkeypatch, users, departments
) -> None:
    monkeypatch.setattr(settings, "ATTACHMENT_STORAGE_DIR", str(tmp_path / "bad"))
    ticket_id = _create_ticket(client, users, departments)
    header = auth_header(client, users["student"].email)

    script = _upload(
        client,
        ticket_id,
        header,
        files={"file": ("script.exe", b"MZ\x00\x00", "application/octet-stream")},
    )
    assert script.status_code == 415
    assert script.json()["code"] == "upload_type_not_allowed"

    fake_pdf = _upload(
        client,
        ticket_id,
        header,
        files={"file": ("fake.pdf", b"not a pdf", "application/pdf")},
    )
    assert fake_pdf.status_code == 415
    assert fake_pdf.json()["code"] == "upload_invalid_pdf"

    assert db_session.scalar(select(func.count(MessageAttachment.id))) == 0
    assert db_session.scalar(select(func.count(Message.id))) == 0


def test_internal_attachment_is_not_notified_or_visible_to_student(
    client, db_session, tmp_path, monkeypatch, users, departments
) -> None:
    monkeypatch.setattr(settings, "ATTACHMENT_STORAGE_DIR", str(tmp_path / "internal"))
    ticket_id = _create_ticket(client, users, departments)
    staff_header = auth_header(client, users["staff"].email)

    # Assign the ticket so the staff user may access it.
    admin_header = auth_header(client, users["admin"].email)
    assignment = client.post(
        f"{TICKETS_URL}/{ticket_id}/assign",
        headers=admin_header,
        json={"assignee_id": users["staff"].id},
    )
    assert assignment.status_code == 200, assignment.text
    notifications_before = db_session.scalar(select(func.count(Notification.id)))

    response = _upload(
        client,
        ticket_id,
        staff_header,
        files={"file": ("internal.md", b"# Internal note", "text/markdown")},
        message_body="Internal evidence",
        is_internal="true",
    )
    assert response.status_code == 201, response.text
    assert db_session.scalar(select(func.count(Notification.id))) == notifications_before

    student_header = auth_header(client, users["student"].email)
    listing = client.get(f"{TICKETS_URL}/{ticket_id}/attachments", headers=student_header)
    assert listing.status_code == 200, listing.text
    assert listing.json()["total"] == 0


def test_another_student_cannot_upload_or_list_attachments(
    client, db_session, tmp_path, monkeypatch, users, departments
) -> None:
    monkeypatch.setattr(settings, "ATTACHMENT_STORAGE_DIR", str(tmp_path / "isolated"))
    ticket_id = _create_ticket(client, users, departments)
    other_header = auth_header(client, users["student2"].email)

    # Cross-student tickets are hidden with 404 rather than revealing existence.
    upload = _upload(client, ticket_id, other_header)
    assert upload.status_code == 404
    listing = client.get(f"{TICKETS_URL}/{ticket_id}/attachments", headers=other_header)
    assert listing.status_code == 404
