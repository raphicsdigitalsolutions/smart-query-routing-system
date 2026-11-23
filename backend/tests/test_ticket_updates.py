"""FR-06: conditional polling endpoint for live ticket status tracking."""

from tests.conftest import auth_header

UPDATES_URL = "/api/v1/tickets/{ticket_id}/updates"


def _create_ticket(client, users, departments) -> int:
    response = client.post(
        "/api/v1/tickets",
        headers=auth_header(client, users["student"].email),
        json={
            "subject": "Live status check",
            "description": "This description is long enough to create a ticket.",
            "department_id": departments["registry"].id,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_ticket_updates_are_scoped_to_authorized_viewers(client, users, departments) -> None:
    ticket_id = _create_ticket(client, users, departments)

    owner = client.get(
        UPDATES_URL.format(ticket_id=ticket_id),
        headers=auth_header(client, users["student"].email),
    )
    assert owner.status_code == 200, owner.text
    assert owner.json()["status"] == "new"
    assert owner.headers["etag"].startswith('"tkt-')

    stranger = client.get(
        UPDATES_URL.format(ticket_id=ticket_id),
        headers=auth_header(client, users["student2"].email),
    )
    assert stranger.status_code == 404


def test_ticket_updates_support_not_modified_polling(client, users, departments) -> None:
    ticket_id = _create_ticket(client, users, departments)
    url = UPDATES_URL.format(ticket_id=ticket_id)
    student_header = auth_header(client, users["student"].email)

    first = client.get(url, headers=student_header)
    assert first.status_code == 200, first.text
    first_etag = first.headers["etag"]
    assert first.headers["cache-control"] == "no-store"

    unchanged = client.get(url, headers={**student_header, "If-None-Match": first_etag})
    assert unchanged.status_code == 304
    assert unchanged.content == b""
    assert unchanged.headers["etag"] == first_etag

    patch = client.patch(
        f"/api/v1/tickets/{ticket_id}",
        headers=auth_header(client, users["admin"].email),
        json={"is_escalated": True},
    )
    assert patch.status_code == 200, patch.text

    changed = client.get(url, headers={**student_header, "If-None-Match": first_etag})
    assert changed.status_code == 200, changed.text
    assert changed.json()["is_escalated"] is True
    assert changed.headers["etag"] != first_etag
