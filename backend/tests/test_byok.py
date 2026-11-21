"""Deterministic BYOK encryption, settings API and AI-run gating tests."""

from __future__ import annotations

import pytest
from sqlalchemy import func, select

from app.agents.services import agent_service
from app.core.config import settings
from app.core.encryption import decrypt_secret, encrypt_secret, make_key_hint
from app.core.errors import AppError
from app.main import app
from app.models import AgentRun, Ticket, TicketAiAnalysis, UserApiKey
from app.services import byok
from tests.ai_helpers import make_llm, valid_classification, valid_draft, valid_routing
from tests.conftest import auth_header

_KEY_A = "sk-test-key-for-user-a-1234567890"
_KEY_B = "sk-test-key-for-user-b-0987654321"


@pytest.fixture(autouse=True)
def _mount_settings_routes():
    """Mount the settings router when the aggregate router has not been updated."""
    path = f"{settings.API_V1_PREFIX}/settings/api-keys"
    if not any(getattr(route, "path", None) == path for route in app.routes):
        from app.api.routes.settings import router as settings_router

        app.include_router(settings_router, prefix=settings.API_V1_PREFIX)
    yield


def _submit_ticket(client, header: dict[str, str], departments) -> int:
    response = client.post(
        "/api/v1/tickets",
        headers=header,
        json={
            "subject": "Password reset question",
            "description": "I cannot access the student portal and need help with my password.",
            "department_id": departments["registry"].id,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _assign(client, admin_header: dict[str, str], ticket_id: int, assignee_id: int) -> None:
    response = client.post(
        f"/api/v1/tickets/{ticket_id}/assign",
        headers=admin_header,
        json={"assignee_id": assignee_id},
    )
    assert response.status_code == 200, response.text


def _save(db_session, user_id: int, api_key: str):
    return byok.save_api_key(db_session, user_id, api_key, validator=lambda _: True)


def test_encryption_roundtrip_hint_and_fail_closed(monkeypatch):
    token = encrypt_secret(_KEY_A)
    assert token != _KEY_A
    assert decrypt_secret(token) == _KEY_A

    hint = make_key_hint(_KEY_A)
    assert hint.endswith(_KEY_A[-4:])
    assert _KEY_A not in hint
    assert hint != _KEY_A

    monkeypatch.setattr(settings, "BYOK_ENCRYPTION_KEY", "")
    with pytest.raises(AppError) as missing:
        encrypt_secret(_KEY_A)
    assert missing.value.status_code == 503
    assert missing.value.code == "secret_store_not_configured"

    monkeypatch.setattr(settings, "BYOK_ENCRYPTION_KEY", "not-a-valid-fernet-key")
    with pytest.raises(AppError) as invalid:
        decrypt_secret(token)
    assert invalid.value.status_code == 503
    assert invalid.value.code == "secret_store_not_configured"


def test_maximum_key_length_fits_encrypted_column() -> None:
    key = "k" * 256
    token = encrypt_secret(key)
    column_limit = UserApiKey.__table__.c.encrypted_key.type.length
    assert column_limit is not None
    assert len(token) <= column_limit
    assert decrypt_secret(token) == key


def test_status_never_returns_secret(client, db_session, users, monkeypatch):
    header = auth_header(client, "grace@university.edu")
    empty = client.get("/api/v1/settings/api-keys", headers=header)
    assert empty.status_code == 200, empty.text
    assert empty.json()["configured"] is False
    assert "api_key" not in empty.json()

    _save(db_session, users["staff"].id, _KEY_A)
    monkeypatch.setattr(byok, "default_validator", lambda _: True)
    stored = client.get("/api/v1/settings/api-keys", headers=header)
    assert stored.status_code == 200, stored.text
    body = stored.text
    assert _KEY_A not in body
    assert stored.json()["configured"] is True
    assert stored.json()["is_valid"] is True
    assert stored.json()["key_hint"].endswith(_KEY_A[-4:])
    assert "encrypted_key" not in stored.json()


def test_user_cannot_read_replace_or_delete_another_users_key(
    client, db_session, users, monkeypatch
):
    _save(db_session, users["staff"].id, _KEY_A)
    original = db_session.scalar(
        select(UserApiKey).where(UserApiKey.user_id == users["staff"].id)
    )
    original_encrypted = original.encrypted_key
    original_hint = original.key_hint

    header_b = auth_header(client, "alan@university.edu")
    monkeypatch.setattr(byok, "default_validator", lambda _: True)

    status_b = client.get("/api/v1/settings/api-keys", headers=header_b)
    assert status_b.status_code == 200
    assert status_b.json()["configured"] is False

    replaced_b = client.put(
        "/api/v1/settings/api-keys", headers=header_b, json={"api_key": _KEY_B}
    )
    assert replaced_b.status_code == 200, replaced_b.text
    assert replaced_b.json()["key_hint"].endswith(_KEY_B[-4:])

    db_session.refresh(original)
    assert original.encrypted_key == original_encrypted
    assert original.key_hint == original_hint
    assert decrypt_secret(original.encrypted_key) == _KEY_A

    deleted_b = client.delete("/api/v1/settings/api-keys", headers=header_b)
    assert deleted_b.status_code == 200, deleted_b.text
    db_session.refresh(original)
    assert original.encrypted_key == original_encrypted
    assert original.key_hint == original_hint

    validate_b = client.post("/api/v1/settings/api-keys/validate", headers=header_b)
    assert validate_b.status_code == 404
    assert validate_b.json()["code"] == "api_key_not_found"


def test_validation_success_and_failure_with_injected_validator(db_session, users):
    status = _save(db_session, users["staff"].id, _KEY_A)
    assert status.is_valid is True
    assert status.validated_at is not None

    passed = byok.validate_api_key(db_session, users["staff"].id, validator=lambda _: True)
    assert passed.is_valid is True
    assert passed.validated_at is not None

    with pytest.raises(AppError) as rejected:
        byok.validate_api_key(db_session, users["staff"].id, validator=lambda _: False)
    assert rejected.value.status_code == 400
    assert rejected.value.code == "invalid_api_key"

    stored = db_session.scalar(
        select(UserApiKey).where(UserApiKey.user_id == users["staff"].id)
    )
    assert stored.is_valid is False
    assert stored.key_hint.endswith(_KEY_A[-4:])
    assert decrypt_secret(stored.encrypted_key) == _KEY_A

    with pytest.raises(AppError) as missing:
        byok.validate_api_key(db_session, users["student"].id, validator=lambda _: True)
    assert missing.value.status_code == 404
    assert missing.value.code == "api_key_not_found"


def test_replace_semantics_keep_one_encrypted_row(db_session, users):
    _save(db_session, users["staff"].id, _KEY_A)
    second = _save(db_session, users["staff"].id, _KEY_B)

    rows = db_session.scalars(
        select(UserApiKey).where(UserApiKey.user_id == users["staff"].id)
    ).all()
    assert len(rows) == 1
    assert second.key_hint.endswith(_KEY_B[-4:])
    assert _KEY_A[-4:] not in (second.key_hint or "")
    assert decrypt_secret(rows[0].encrypted_key) == _KEY_B

    total = db_session.scalar(select(func.count()).select_from(UserApiKey))
    assert total == 1


def test_delete_removes_only_the_authenticated_users_key(client, db_session, users):
    _save(db_session, users["staff"].id, _KEY_A)
    header = auth_header(client, "grace@university.edu")
    deleted = client.delete("/api/v1/settings/api-keys", headers=header)
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["configured"] is False
    assert db_session.scalar(select(UserApiKey).where(UserApiKey.user_id == users["staff"].id)) is None

    again = client.delete("/api/v1/settings/api-keys", headers=header)
    assert again.status_code == 404
    assert again.json()["code"] == "api_key_not_found"


def test_ai_endpoint_requires_personal_key_without_fallback(
    client, db_session, users, departments, monkeypatch
):
    monkeypatch.setattr(settings, "ALLOW_GLOBAL_OPENAI_FALLBACK", False)
    monkeypatch.setattr(settings, "ENVIRONMENT", "testing")

    student_header = auth_header(client, "ada@university.edu")
    staff_header = auth_header(client, "grace@university.edu")
    admin_header = auth_header(client, "alice@university.edu")
    ticket_id = _submit_ticket(client, student_header, departments)
    _assign(client, admin_header, ticket_id, users["staff"].id)

    response = client.post(f"/api/v1/ai/tickets/{ticket_id}/analyze", headers=staff_header)
    assert response.status_code == 402, response.text
    assert response.json()["code"] == "ai_personal_key_required"
    assert db_session.scalar(
        select(TicketAiAnalysis).where(TicketAiAnalysis.ticket_id == ticket_id)
    ) is None


def test_ai_endpoint_uses_personal_key_with_injected_llm(
    client, db_session, users, departments, monkeypatch
):
    monkeypatch.setattr(settings, "ALLOW_GLOBAL_OPENAI_FALLBACK", False)
    monkeypatch.setattr(byok, "default_validator", lambda _: True)

    student_header = auth_header(client, "ada@university.edu")
    staff_header = auth_header(client, "grace@university.edu")
    admin_header = auth_header(client, "alice@university.edu")
    ticket_id = _submit_ticket(client, student_header, departments)
    _assign(client, admin_header, ticket_id, users["staff"].id)

    saved = client.put(
        "/api/v1/settings/api-keys", headers=staff_header, json={"api_key": _KEY_A}
    )
    assert saved.status_code == 200, saved.text

    llm, _ = make_llm(
        [
            valid_classification(),
            valid_routing(departments["registry"].id),
            valid_draft(),
        ]
    )
    seen: list[str | None] = []

    def factory(api_key: str | None = None):
        seen.append(api_key)
        return llm

    monkeypatch.setattr(agent_service, "get_llm_service", factory)

    response = client.post(f"/api/v1/ai/tickets/{ticket_id}/analyze", headers=staff_header)
    assert response.status_code == 201, response.text
    assert response.json()["status"] == "completed"
    assert _KEY_A not in response.text
    assert seen == [_KEY_A]

    stored_key = db_session.scalar(
        select(UserApiKey).where(UserApiKey.user_id == users["staff"].id)
    )
    assert stored_key is not None
    assert stored_key.last_used_at is not None

    analysis = db_session.scalar(
        select(TicketAiAnalysis).where(TicketAiAnalysis.ticket_id == ticket_id)
    )
    assert analysis is not None
    run = db_session.scalar(select(AgentRun).where(AgentRun.analysis_id == analysis.id))
    assert run is not None
    assert run.ticket_id == ticket_id
    assert run.requested_by_id == users["staff"].id
    assert run.status == "completed"
    assert run.model == settings.OPENAI_MODEL
    assert run.prompt_tokens == 30
    assert run.completion_tokens == 60
    assert run.permission_outcome == "allowed"
    assert run.duration_ms is not None and run.duration_ms >= 0

    ticket = db_session.get(Ticket, ticket_id)
    assert ticket is not None
