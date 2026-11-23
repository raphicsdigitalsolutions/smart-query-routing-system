"""Local-only E2E server: seed a disposable SQLite DB, then serve the API.

Never points at a production database. Playwright starts this process with a
SQLite DATABASE_URL restricted to the frontend-next/.e2e directory.
"""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("EMAIL_NOTIFICATIONS_ENABLED", "false")
os.environ.setdefault("WHATSAPP_ENABLED", "false")

# SQLite cannot create its database file when the parent directory is absent.
# Playwright owns this disposable directory and ignores it from Git.
e2e_dir = Path(__file__).resolve().parents[1] / "frontend-next" / ".e2e"
e2e_dir.mkdir(parents=True, exist_ok=True)
(e2e_dir / "attachments").mkdir(parents=True, exist_ok=True)

from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.security import hash_password  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import engine  # noqa: E402
from app.models import Department, Ticket, User  # noqa: E402

E2E_PASSWORD = "E2ePassword123!"


def seed() -> None:
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        registry = Department(name="Registry", description="Student records")
        scholarships = Department(name="Scholarships", description="Awards")
        db.add_all([registry, scholarships])
        db.flush()

        student = User(
            full_name="E2E Student",
            email="e2e.student@university.edu",
            password_hash=hash_password(E2E_PASSWORD),
            role="student",
        )
        student_two = User(
            full_name="E2E Other Student",
            email="e2e.student2@university.edu",
            password_hash=hash_password(E2E_PASSWORD),
            role="student",
        )
        staff = User(
            full_name="E2E Staff",
            email="e2e.staff@university.edu",
            password_hash=hash_password(E2E_PASSWORD),
            role="staff",
            department_id=registry.id,
        )
        admin = User(
            full_name="E2E Admin",
            email="e2e.admin@university.edu",
            password_hash=hash_password(E2E_PASSWORD),
            role="admin",
        )
        db.add_all([student, student_two, staff, admin])
        db.flush()

        db.add(
            Ticket(
                public_reference="E2E-PRIVATE-0001",
                subject="Private isolation ticket",
                description="This ticket belongs to the other student and must not leak.",
                priority="normal",
                status="new",
                channel="web",
                student_id=student_two.id,
                department_id=registry.id,
            )
        )
        db.commit()

    print("E2E database seeded", flush=True)


if __name__ == "__main__":
    seed()
    import uvicorn

    port = int(os.environ.get("E2E_API_PORT", "8100"))
    uvicorn.run("app.main:app", host="127.0.0.1", port=port, log_level="warning")
