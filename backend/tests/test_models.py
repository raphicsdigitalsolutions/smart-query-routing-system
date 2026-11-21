"""ORM relationship, default and constraint tests on an isolated in-memory DB.

These tables exist only for the duration of a test. Production schema changes
are exclusively managed by Alembic migrations.
"""

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import configure_mappers, sessionmaker

from app.models import Base, Department, Message, Ticket, User

TEST_HASH = "not-a-real-argon2-hash-test-only"


@pytest.fixture()
def db_session():
    configure_mappers()
    test_engine = create_engine("sqlite://")
    Base.metadata.create_all(test_engine)
    test_session = sessionmaker(bind=test_engine, expire_on_commit=False)
    with test_session() as session:
        yield session
    test_engine.dispose()


def test_relationships_navigate_across_all_entities(db_session) -> None:
    department = Department(name="Student Affairs", description="Student support")
    student = User(
        full_name="Ada Student",
        email="ada@university.edu",
        password_hash=TEST_HASH,
        role="student",
    )
    staff = User(
        full_name="Grace Staff",
        email="grace@university.edu",
        password_hash=TEST_HASH,
        role="staff",
        department=department,
    )
    ticket = Ticket(
        public_reference="TKT-0001",
        subject="Scholarship deadline",
        description="Could you confirm the deadline?",
        student=student,
        assignee=staff,
        department=department,
    )
    message = Message(ticket=ticket, sender=student, message_body="Thank you")

    db_session.add_all([department, student, staff, ticket, message])
    db_session.commit()

    assert ticket.student.email == "ada@university.edu"
    assert ticket.assignee.full_name == "Grace Staff"
    assert ticket.department is department
    assert message.ticket is ticket
    assert message.sender is student
    assert student.tickets_submitted == [ticket]
    assert staff.tickets_assigned == [ticket]
    assert department.users == [staff]
    assert department.tickets == [ticket]
    assert ticket.messages == [message]
    assert student.messages_sent == [message]


def test_duplicate_email_is_rejected(db_session) -> None:
    db_session.add(User(full_name="First", email="duplicate@university.edu", password_hash=TEST_HASH))
    db_session.commit()
    db_session.add(User(full_name="Second", email="duplicate@university.edu", password_hash=TEST_HASH))

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_defaults_and_timestamps_are_populated(db_session) -> None:
    department = Department(name="Registry")
    student = User(full_name="Noah", email="noah@university.edu", password_hash=TEST_HASH)
    ticket = Ticket(
        public_reference="TKT-0002",
        subject="Transcript request",
        description="Please send my transcript.",
        student=student,
        department=department,
    )

    db_session.add(ticket)
    db_session.commit()

    assert ticket.status == "new"
    assert ticket.priority == "normal"
    assert student.role == "student"
    assert student.is_active is True
    assert department.is_active is True
    assert ticket.created_at is not None
    assert ticket.updated_at is not None
    assert ticket.messages == []


def test_foreign_keys_and_check_constraints_are_declared() -> None:
    tickets = inspect(Base.metadata.tables["tickets"])
    referenced = {fk.target_fullname.split(".")[0] for fk in tickets.foreign_keys}
    assert {"users", "departments"}.issubset(referenced)

    constraint_names = {constraint.name for constraint in tickets.constraints}
    assert "ck_tickets_priority_valid" in constraint_names
    assert "ck_tickets_status_valid" in constraint_names

    messages = inspect(Base.metadata.tables["messages"])
    message_targets = {fk.target_fullname.split(".")[0] for fk in messages.foreign_keys}
    assert {"tickets", "users"}.issubset(message_targets)
