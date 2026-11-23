"""Disposable local demonstration server and deterministic test-data seeder.

Safety guarantees:
- Always uses an isolated, disposable SQLite database under
  ``frontend-next/.e2e/demo_local_test.db``.
- Explicitly overrides any environment/file ``DATABASE_URL`` and ``OPENAI_API_KEY``
  before importing ``app`` so it can NEVER connect to a hosted or production
  database or use a global API key.
- Seeds all four roles (student, staff, hod, admin), four university
  departments, an active instructor leave window, approved knowledge base
  articles, a broadcast announcement, a pre-computed grounded AI analysis draft
  waiting at the human approval gate, an overdue ticket ready for the 24h SLA
  escalation sweep, and a second student's private ticket for role-isolation
  verification.
"""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography.fernet import Fernet

ROOT_DIR = Path(__file__).resolve().parents[1]
DEMO_DIR = ROOT_DIR / "frontend-next" / ".e2e"
DEMO_DIR.mkdir(parents=True, exist_ok=True)
(DEMO_DIR / "demo_attachments").mkdir(parents=True, exist_ok=True)

DEMO_DB_PATH = (DEMO_DIR / "demo_local_test.db").as_posix()
FERNET_KEY_FILE = DEMO_DIR / "demo_fernet.txt"
if FERNET_KEY_FILE.is_file():
    _DEMO_FERNET = FERNET_KEY_FILE.read_text(encoding="utf-8").strip()
else:
    _DEMO_FERNET = Fernet.generate_key().decode()
    FERNET_KEY_FILE.write_text(_DEMO_FERNET, encoding="utf-8")

# Force disposable local-only settings before importing app modules.
os.environ["ENVIRONMENT"] = "development"
os.environ["DEBUG"] = "false"
os.environ["DATABASE_URL"] = f"sqlite:///{DEMO_DB_PATH}"
os.environ["JWT_SECRET_KEY"] = "local-test-demo-jwt-secret-not-for-production-0123456789"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "60"
os.environ["ALLOW_GLOBAL_OPENAI_FALLBACK"] = "false"
os.environ["OPENAI_API_KEY"] = ""
os.environ["BYOK_" + "ENCRYPTION_KEY"] = _DEMO_FERNET
os.environ["EMAIL_NOTIFICATIONS_ENABLED"] = "false"
os.environ["WHATSAPP_ENABLED"] = "false"
os.environ["GOOGLE_OAUTH_ENABLED"] = "false"
os.environ["ESCALATION_CRON_SECRET"] = "local-test-demo-cron-secret-not-for-production"
os.environ["INTAKE_WEBHOOK_TOKEN"] = "local-test-demo-intake-token-not-for-production"
os.environ["ATTACHMENT_STORAGE_DIR"] = str(DEMO_DIR / "demo_attachments")
os.environ["MALWARE_SCAN_ENABLED"] = "false"

from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.agents.services.demo_llm import is_demo_api_key  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import engine  # noqa: E402
from app.models import (  # noqa: E402
    Announcement,
    AuditLog,
    Department,
    InstructorLeave,
    KnowledgeDocument,
    Message,
    Notification,
    Ticket,
    TicketAiAnalysis,
    TicketAssignmentHistory,
    TicketStatusHistory,
    User,
)
from app.services import byok  # noqa: E402

DEMO_PASSWORD = "LocalTestDemo123!"

_real_openai_validator = byok.validate_with_openai


def _demo_aware_validator(api_key: str) -> bool:
    """Allow local demo keys offline while preserving live OpenAI validation for real keys."""
    if is_demo_api_key(api_key):
        return True
    return _real_openai_validator(api_key)


byok.default_validator = _demo_aware_validator


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _ensure_demo_reference_data(db: Session) -> None:
    """Ensure existing disposable demo databases contain the full approved KB set."""
    now_utc = datetime.now(timezone.utc)
    dept_by_name = {d.name: d for d in db.scalars(select(Department)).all()}
    admin_user = db.scalar(select(User).where(User.role == "admin").limit(1))
    if admin_user is None:
        return

    dept_updates = {
        "Computer Science": (
            "Computer Science coursework, Java programming assignment, object-oriented "
            "programming OOP concepts, classes, objects, inheritance, data structures, "
            "algorithm lab, compiler exam, software engineering grading rubric"
        ),
        "Registry": (
            "Student records, academic transcript verification, official transcript, "
            "enrollment verification, semester registration, degree audit, medical deferral"
        ),
        "Scholarships & Financial Aid": (
            "Scholarships, financial aid, scholarship payment delay, tuition fee waiver, "
            "stipend disbursement, grant application, merit award documents"
        ),
        "IT Services": (
            "Technology support, student portal password reset, account access recovery, "
            "campus Wi-Fi, LMS portal login, VPN access, university email account MFA reset"
        ),
    }
    for name, desc in dept_updates.items():
        if name in dept_by_name:
            dept_by_name[name].description = desc

    required_docs = [
        (
            "KB-CS-102",
            "CS Java & Object-Oriented Programming (OOP) Coursework Support Policy",
            dept_by_name.get("Computer Science"),
            (
                "Computer Science Java & Object-Oriented Programming (OOP) Coursework Support Policy (KB-CS-102):\n"
                "1. Students seeking help understanding Java programming assignments and core object-oriented "
                "programming (OOP) concepts—including classes, objects, constructors, encapsulation, inheritance, "
                "and polymorphism—are assigned to an available Computer Science instructor for academic guidance.\n"
                "2. Assigned Computer Science instructors provide 1-on-1 concept walkthroughs, starter-code reviews, "
                "and debugging guidance during weekly CS lab consultation hours or via ticket reply within 1 business day.\n"
                "3. Students should share the specific Java class or inheritance hierarchy they are working on so the "
                "assigned instructor (such as Dr. Grace Hopper) can provide targeted OOP examples and explanations "
                "without disclosing full assignment solutions."
            ),
        ),
        (
            "KB-IT-401",
            "IT Services Student Portal Account Access & Password Reset Policy",
            dept_by_name.get("IT Services"),
            (
                "IT Services Student Portal Account Access & Password Reset Policy (KB-IT-401):\n"
                "1. Students who cannot sign in to the student portal or LMS due to a forgotten password or expired "
                "credentials can initiate an immediate password reset through the IT Self-Service Portal using their "
                "registered recovery method.\n"
                "2. If an account is locked after repeated login attempts or requires a multi-factor authentication (MFA) "
                "reset, IT Services Helpdesk verifies the student's university ID and issues a temporary access reset "
                "within 2 business hours.\n"
                "3. Never share passwords or verification codes inside ticket messages; IT Services staff will only reset "
                "credentials through the official portal workflow."
            ),
        ),
        (
            "KB-FIN-301",
            "Merit Scholarship & Stipend Disbursement Policy",
            dept_by_name.get("Scholarships & Financial Aid"),
            (
                "Merit Scholarship & Stipend Disbursement Guidelines (KB-FIN-301):\n"
                "1. Continuing merit scholarship recipients must upload a signed enrollment confirmation "
                "form and maintain a minimum cumulative GPA of 3.50.\n"
                "2. Stipends are disbursed in week 3 of the semester after Registry enrollment lock.\n"
                "3. If a scholarship or financial aid stipend payment is delayed beyond week 3, the Scholarships & "
                "Financial Aid Office verifies Registry enrollment lock and bank disbursement details and resolves "
                "payment delays within 3 business days."
            ),
        ),
    ]
    for source_key, title, dept, text in required_docs:
        if dept is None:
            continue
        existing = db.scalar(
            select(KnowledgeDocument).where(KnowledgeDocument.source_key == source_key).limit(1)
        )
        if existing is None:
            db.add(
                KnowledgeDocument(
                    title=title,
                    source_key=source_key,
                    version=1,
                    source_type="text",
                    checksum=_sha256(text),
                    content_text=text,
                    department_id=dept.id,
                    uploaded_by_id=admin_user.id,
                    approved_by_id=admin_user.id,
                    approved_at=now_utc - timedelta(days=10),
                    is_approved=True,
                    is_active=True,
                )
            )
        else:
            existing.title = title
            existing.content_text = text
            existing.checksum = _sha256(text)
            existing.department_id = dept.id
            existing.is_approved = True
            existing.is_active = True
    db.commit()


def seed_demo_database(*, reset: bool = False) -> None:
    """Create and deterministically seed the disposable local demo database."""
    if reset:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        if not reset and db.scalar(select(User.id).limit(1)) is not None:
            _ensure_demo_reference_data(db)
            print(f"Preserving existing disposable demo database at: {DEMO_DB_PATH}", flush=True)
            return

    now_utc = datetime.now(timezone.utc)
    now_naive = now_utc.replace(tzinfo=None)

    with Session(engine) as db:
        # 1. University departments (persisted name & description drive auto_routing.py)
        dept_cs = Department(
            name="Computer Science",
            description=(
                "Computer Science coursework, programming assignment, data structures, "
                "algorithm lab, compiler exam, software engineering grading rubric"
            ),
            is_active=True,
        )
        dept_registry = Department(
            name="Registry",
            description=(
                "Student records, academic transcript, enrollment verification, "
                "semester registration, degree audit, medical deferral"
            ),
            is_active=True,
        )
        dept_finance = Department(
            name="Scholarships & Financial Aid",
            description=(
                "Scholarships, financial aid, tuition fee waiver, stipend disbursement, "
                "grant application, merit award documents"
            ),
            is_active=True,
        )
        dept_it = Department(
            name="IT Services",
            description=(
                "Technology support, campus Wi-Fi, LMS portal login, VPN access, "
                "university email account MFA reset"
            ),
            is_active=True,
        )
        db.add_all([dept_cs, dept_registry, dept_finance, dept_it])
        db.flush()

        # 2. Users across all 4 roles
        password_hash = hash_password(DEMO_PASSWORD)
        student_ada = User(
            full_name="Ada Lovelace (Student)",
            email="demo.student@university.edu",
            password_hash=password_hash,
            role="student",
            is_active=True,
        )
        student_alan = User(
            full_name="Alan Turing (Student 2)",
            email="demo.student2@university.edu",
            password_hash=password_hash,
            role="student",
            is_active=True,
        )
        staff_grace = User(
            full_name="Dr. Grace Hopper (CS Instructor)",
            email="demo.staff.cs1@university.edu",
            password_hash=password_hash,
            role="staff",
            department_id=dept_cs.id,
            is_active=True,
        )
        staff_dijkstra = User(
            full_name="Dr. Edsger Dijkstra (CS Instructor - On Leave)",
            email="demo.staff.cs2@university.edu",
            password_hash=password_hash,
            role="staff",
            department_id=dept_cs.id,
            is_active=True,
        )
        staff_margaret = User(
            full_name="Prof. Margaret Hamilton (Registry Staff)",
            email="demo.staff.reg@university.edu",
            password_hash=password_hash,
            role="staff",
            department_id=dept_registry.id,
            is_active=True,
        )
        staff_knuth = User(
            full_name="Prof. Donald Knuth (Scholarships Staff)",
            email="demo.staff.fin@university.edu",
            password_hash=password_hash,
            role="staff",
            department_id=dept_finance.id,
            is_active=True,
        )
        hod_liskov = User(
            full_name="Dr. Barbara Liskov (CS HOD)",
            email="demo.hod.cs@university.edu",
            password_hash=password_hash,
            role="hod",
            department_id=dept_cs.id,
            is_active=True,
        )
        hod_tim = User(
            full_name="Dr. Tim Berners-Lee (Registry HOD)",
            email="demo.hod.reg@university.edu",
            password_hash=password_hash,
            role="hod",
            department_id=dept_registry.id,
            is_active=True,
        )
        admin_mccarthy = User(
            full_name="Prof. John McCarthy (System Admin)",
            email="demo.admin@university.edu",
            password_hash=password_hash,
            role="admin",
            is_active=True,
        )
        db.add_all(
            [
                student_ada,
                student_alan,
                staff_grace,
                staff_dijkstra,
                staff_margaret,
                staff_knuth,
                hod_liskov,
                hod_tim,
                admin_mccarthy,
            ]
        )
        db.flush()

        # 3. Active Instructor Leave window for Dr. Edsger Dijkstra (FR-13)
        # Excludes him from automatic routing; triggers auto-reply if manually assigned.
        leave_dijkstra = InstructorLeave(
            user_id=staff_dijkstra.id,
            start_at=now_utc - timedelta(days=2),
            end_at=now_utc + timedelta(days=5),
            reason="Attending ACM Symposium on Operating Systems Principles",
            auto_reply=(
                "Thank you for your query. I am currently on approved academic leave "
                "attending the ACM Symposium and have limited access to messages. "
                "Urgent Computer Science queries are being handled by Dr. Grace Hopper "
                "or our Head of Department, Dr. Barbara Liskov."
            ),
            is_active=True,
            created_by_id=staff_dijkstra.id,
        )
        db.add(leave_dijkstra)

        # 4. Approved Knowledge Base Documents (FR-03 / FR-05 grounded citations)
        kb_cs_text = (
            "Computer Science Assessment & Grading Rubric Policy (KB-CS-101):\n"
            "1. All programming assignments are evaluated against automated unit tests (60%), "
            "code architecture & complexity analysis (25%), and documentation (15%).\n"
            "2. Students may request a formal rubric breakdown or regrade within 7 calendar days "
            "of grade publication by submitting a ticket routed to Computer Science.\n"
            "3. Late submissions incur a 10% deduction per 24 hours unless an approved medical "
            "or registry deferral is attached."
        )
        kb_reg_text = (
            "Official Academic Transcript & Verification Policy (KB-REG-201):\n"
            "1. Standard official transcript verification takes 2 business days.\n"
            "2. Expedited graduate fellowship or scholarship verifications are processed within "
            "24 hours by the Registry Office upon uploading the fellowship reference letter."
        )
        kb_fin_text = (
            "Merit Scholarship & Stipend Disbursement Guidelines (KB-FIN-301):\n"
            "1. Continuing merit scholarship recipients must upload a signed enrollment confirmation "
            "form and maintain a minimum cumulative GPA of 3.50.\n"
            "2. Stipends are disbursed in week 3 of the semester after Registry enrollment lock."
        )
        kb_cs = KnowledgeDocument(
            title="CS Programming Assignment & Regrade Policy",
            source_key="KB-CS-101",
            version=1,
            source_type="text",
            checksum=_sha256(kb_cs_text),
            content_text=kb_cs_text,
            department_id=dept_cs.id,
            uploaded_by_id=hod_liskov.id,
            approved_by_id=admin_mccarthy.id,
            approved_at=now_utc - timedelta(days=10),
            is_approved=True,
            is_active=True,
        )
        kb_reg = KnowledgeDocument(
            title="Registry Transcript & Fellowship Verification Policy",
            source_key="KB-REG-201",
            version=1,
            source_type="text",
            checksum=_sha256(kb_reg_text),
            content_text=kb_reg_text,
            department_id=dept_registry.id,
            uploaded_by_id=hod_tim.id,
            approved_by_id=admin_mccarthy.id,
            approved_at=now_utc - timedelta(days=10),
            is_approved=True,
            is_active=True,
        )
        kb_fin = KnowledgeDocument(
            title="Merit Scholarship & Stipend Disbursement Policy",
            source_key="KB-FIN-301",
            version=1,
            source_type="text",
            checksum=_sha256(kb_fin_text),
            content_text=kb_fin_text,
            department_id=dept_finance.id,
            uploaded_by_id=admin_mccarthy.id,
            approved_by_id=admin_mccarthy.id,
            approved_at=now_utc - timedelta(days=10),
            is_approved=True,
            is_active=True,
        )
        db.add_all([kb_cs, kb_reg, kb_fin])
        db.flush()
        _ensure_demo_reference_data(db)

        # 5. Active Broadcast Announcement (FR-11)
        announcement = Announcement(
            title="Spring Semester Scholarship Verification & CS Lab Deadlines",
            body=(
                "Students submitting scholarship verification documents or Computer Science "
                "grading queries can use automatic routing in the Smart Query Hub. "
                "All unresolved tickets are monitored under our 24-hour SLA policy."
            ),
            audience_roles_json=["student", "staff", "hod", "admin"],
            department_id=None,
            created_by_id=admin_mccarthy.id,
            published_at=now_utc - timedelta(hours=6),
            is_active=True,
        )
        db.add(announcement)

        # 6. Ticket 1: Auto-routed CS ticket assigned to Dr. Grace Hopper with pre-seeded AI draft
        tkt_cs = Ticket(
            public_reference="TKT-DEMO0001",
            subject="Question about CS programming assignment grading rubric",
            description=(
                "Hello Computer Science faculty, I received my score for the data structures "
                "programming assignment and would like to know how the automated unit tests "
                "and complexity analysis weights are applied, and the deadline for a regrade review."
            ),
            category="programming",
            priority="normal",
            status="assigned",
            is_escalated=False,
            student_id=student_ada.id,
            assigned_to=staff_grace.id,
            department_id=dept_cs.id,
            channel="web",
            auto_routed=True,
            created_at=now_naive - timedelta(hours=2),
            updated_at=now_naive - timedelta(hours=2),
        )
        # 7. Ticket 2: Overdue Registry ticket (30 hours old, >24h SLA) ready for escalation demo
        tkt_overdue = Ticket(
            public_reference="TKT-DEMO0002",
            subject="Urgent academic transcript verification for graduate fellowship",
            description=(
                "I need an official academic transcript verification sent for my graduate "
                "fellowship application. The request was submitted over 24 hours ago."
            ),
            category="transcript",
            priority="high",
            status="in_progress",
            is_escalated=False,
            student_id=student_ada.id,
            assigned_to=staff_margaret.id,
            department_id=dept_registry.id,
            channel="web",
            auto_routed=True,
            created_at=now_naive - timedelta(hours=30),
            updated_at=now_naive - timedelta(hours=28),
        )
        # 8. Ticket 3: Other student's private ticket (Alan Turing) for role/student isolation demo
        tkt_private = Ticket(
            public_reference="TKT-DEMO0003",
            subject="Private medical semester deferral request - Alan Turing",
            description=(
                "Confidential medical deferral documentation for Alan Turing. "
                "Must never be accessible to any other student account."
            ),
            category="deferral",
            priority="high",
            status="new",
            is_escalated=False,
            student_id=student_alan.id,
            assigned_to=None,
            department_id=dept_registry.id,
            channel="web",
            auto_routed=False,
            created_at=now_naive - timedelta(hours=4),
            updated_at=now_naive - timedelta(hours=4),
        )
        # 9. Ticket 4: Ticket with both a public reply and an internal staff-only note
        tkt_notes = Ticket(
            public_reference="TKT-DEMO0004",
            subject="Scholarship stipend disbursement schedule and enrollment form",
            description=(
                "Could you confirm when the merit scholarship stipend is disbursed and "
                "which form I need to upload?"
            ),
            category="scholarship",
            priority="normal",
            status="waiting_for_student",
            is_escalated=False,
            student_id=student_ada.id,
            assigned_to=staff_knuth.id,
            department_id=dept_finance.id,
            channel="web",
            auto_routed=True,
            first_response_at=now_naive - timedelta(hours=3),
            created_at=now_naive - timedelta(hours=5),
            updated_at=now_naive - timedelta(hours=3),
        )
        db.add_all([tkt_cs, tkt_overdue, tkt_private, tkt_notes])
        db.flush()

        # Status and assignment histories
        db.add_all(
            [
                TicketStatusHistory(
                    ticket_id=tkt_cs.id,
                    from_status=None,
                    to_status="new",
                    changed_by_id=student_ada.id,
                    note="Ticket submitted",
                ),
                TicketStatusHistory(
                    ticket_id=tkt_cs.id,
                    from_status="new",
                    to_status="assigned",
                    changed_by_id=None,
                    note="Automatically routed to an available instructor (Dr. Dijkstra excluded on active leave)",
                ),
                TicketAssignmentHistory(
                    ticket_id=tkt_cs.id,
                    from_assignee_id=None,
                    to_assignee_id=staff_grace.id,
                    changed_by_id=None,
                ),
                TicketStatusHistory(
                    ticket_id=tkt_overdue.id,
                    from_status=None,
                    to_status="new",
                    changed_by_id=student_ada.id,
                    note="Ticket submitted",
                    created_at=now_naive - timedelta(hours=30),
                ),
                TicketStatusHistory(
                    ticket_id=tkt_overdue.id,
                    from_status="new",
                    to_status="in_progress",
                    changed_by_id=staff_margaret.id,
                    note="Registry review started",
                    created_at=now_naive - timedelta(hours=28),
                ),
                TicketAssignmentHistory(
                    ticket_id=tkt_overdue.id,
                    from_assignee_id=None,
                    to_assignee_id=staff_margaret.id,
                    changed_by_id=None,
                    created_at=now_naive - timedelta(hours=30),
                ),
                TicketStatusHistory(
                    ticket_id=tkt_private.id,
                    from_status=None,
                    to_status="new",
                    changed_by_id=student_alan.id,
                    note="Ticket submitted",
                ),
                TicketStatusHistory(
                    ticket_id=tkt_notes.id,
                    from_status=None,
                    to_status="new",
                    changed_by_id=student_ada.id,
                    note="Ticket submitted",
                ),
                TicketStatusHistory(
                    ticket_id=tkt_notes.id,
                    from_status="new",
                    to_status="waiting_for_student",
                    changed_by_id=staff_knuth.id,
                    note="Requested signed enrollment confirmation form",
                ),
                TicketAssignmentHistory(
                    ticket_id=tkt_notes.id,
                    from_assignee_id=None,
                    to_assignee_id=staff_knuth.id,
                    changed_by_id=None,
                ),
            ]
        )

        # Public reply + internal staff note on Ticket 4 (D-DATA-04 internal-note privacy demo)
        msg_public = Message(
            ticket_id=tkt_notes.id,
            sender_id=staff_knuth.id,
            message_body=(
                "Hello Ada, per policy KB-FIN-301, merit scholarship stipends are disbursed "
                "in Week 3 after Registry enrollment lock. Please upload your signed "
                "enrollment confirmation form to this ticket."
            ),
            is_internal=False,
        )
        msg_internal = Message(
            ticket_id=tkt_notes.id,
            sender_id=staff_knuth.id,
            message_body=(
                "INTERNAL STAFF NOTE (Never shown to students): Verified Ada's 3.85 GPA in "
                "the Financial Aid ledger. Ready to release disbursement once the PDF is attached."
            ),
            is_internal=True,
        )
        db.add_all([msg_public, msg_internal])

        # Pre-computed grounded AI analysis & unapproved draft on Ticket 1 (FR-03 / FR-05 demo)
        ai_analysis = TicketAiAnalysis(
            ticket_id=tkt_cs.id,
            requested_by_id=staff_grace.id,
            version=1,
            status="completed",
            is_current=True,
            classification_json={
                "intent": "grading_policy_inquiry",
                "category": "Computer Science Coursework",
                "urgency": "normal",
                "language": "en",
                "confidence": 0.94,
                "entities": ["data structures", "programming assignment", "grading rubric", "regrade"],
                "rationale": (
                    "The student is asking for the programming assignment rubric breakdown "
                    "and regrade request window under Computer Science policy."
                ),
            },
            priority_recommendation="normal",
            department_recommendation_json={
                "department_id": dept_cs.id,
                "department_name": dept_cs.name,
                "confidence": 0.96,
                "reason": "Matched Computer Science programming assignment and grading rubric keywords.",
            },
            staff_recommendation_json={
                "staff_id": staff_grace.id,
                "staff_name": staff_grace.full_name,
                "confidence": 0.92,
                "reason": "Least-loaded active Computer Science instructor not on leave.",
            },
            knowledge_sources_json=[
                {
                    "source_id": "KB-CS-101",
                    "title": "CS Programming Assignment & Regrade Policy",
                    "excerpt": (
                        "All programming assignments are evaluated against automated unit tests (60%), "
                        "code architecture & complexity analysis (25%), and documentation (15%). "
                        "Students may request a formal rubric breakdown or regrade within 7 calendar days."
                    ),
                    "relevance_score": 0.95,
                }
            ],
            draft_json={
                "body": (
                    "Hello Ada,\n\n"
                    "Under the Computer Science Assessment & Grading Rubric Policy [KB-CS-101], "
                    "your data structures programming assignment is weighted as follows:\n"
                    "- Automated unit tests: 60%\n"
                    "- Code architecture & complexity analysis: 25%\n"
                    "- Documentation: 15%\n\n"
                    "You may request a formal rubric breakdown or regrade within 7 calendar days "
                    "of grade publication [KB-CS-101]. Please reply to this ticket with your "
                    "submission commit ID so I can attach your detailed test log.\n\n"
                    "Best regards,\n"
                    "Dr. Grace Hopper"
                ),
                "language": "en",
                "confidence": 0.94,
                "source_ids": ["KB-CS-101"],
                "needs_staff_review": False,
            },
            validation_json={
                "passed": True,
                "overall_confidence": 0.94,
                "issues": [],
            },
            no_evidence=False,
            confidence=0.94,
            abstention_reason=None,
            execution_metadata_json=[
                {"node": "classification", "status": "ok", "duration_ms": 180, "model": "gpt-4o-mini"},
                {"node": "routing", "status": "ok", "duration_ms": 45, "model": "deterministic"},
                {"node": "knowledge_research", "status": "ok", "duration_ms": 38, "model": "deterministic"},
                {"node": "response_drafting", "status": "ok", "duration_ms": 310, "model": "gpt-4o-mini"},
                {"node": "validation", "status": "ok", "duration_ms": 22, "model": "deterministic"},
            ],
            approved_by_id=None,
            approved_at=None,
            approved_message_id=None,
        )
        db.add(ai_analysis)

        # Seed representative audit log entries (FR-14)
        db.add_all(
            [
                AuditLog(
                    actor_id=student_ada.id,
                    actor_role="student",
                    action="ticket.created",
                    entity_type="ticket",
                    entity_id=str(tkt_cs.id),
                    details={"public_reference": tkt_cs.public_reference, "department_id": dept_cs.id},
                    is_override=False,
                ),
                AuditLog(
                    actor_id=student_ada.id,
                    actor_role="student",
                    action="ticket.auto_routed",
                    entity_type="ticket",
                    entity_id=str(tkt_cs.id),
                    details={
                        "public_reference": tkt_cs.public_reference,
                        "department_id": dept_cs.id,
                        "keywords": "assignment,grading,programming,rubric",
                    },
                    is_override=False,
                ),
                AuditLog(
                    actor_id=None,
                    actor_role="system",
                    action="ticket.instructor_auto_assigned",
                    entity_type="ticket",
                    entity_id=str(tkt_cs.id),
                    details={
                        "public_reference": tkt_cs.public_reference,
                        "department_id": dept_cs.id,
                        "assignee_id": staff_grace.id,
                        "reason": "least_open_workload_then_full_name_then_id",
                        "excluded_on_leave_count": 1,
                        "active_load": 0,
                    },
                    is_override=False,
                ),
                AuditLog(
                    actor_id=staff_dijkstra.id,
                    actor_role="staff",
                    action="leave.created",
                    entity_type="leave",
                    entity_id="1",
                    details={"user_id": staff_dijkstra.id, "reason": "ACM Symposium"},
                    is_override=False,
                ),
                AuditLog(
                    actor_id=staff_grace.id,
                    actor_role="staff",
                    action="ai.analysis_created",
                    entity_type="ticket",
                    entity_id=str(tkt_cs.id),
                    details={"version": 1, "validation_passed": True},
                    is_override=False,
                ),
            ]
        )

        # In-app notification rows (FR-08)
        db.add_all(
            [
                Notification(
                    ticket_id=tkt_cs.id,
                    recipient_user_id=staff_grace.id,
                    channel="in_app",
                    event_type="ticket.assigned",
                    subject=f"Ticket assigned {tkt_cs.public_reference}",
                    body=f"Ticket {tkt_cs.public_reference} was automatically routed and assigned to you.",
                    status="sent",
                    attempts=1,
                    sent_at=now_naive - timedelta(hours=2),
                    is_internal=False,
                ),
                Notification(
                    ticket_id=tkt_notes.id,
                    recipient_user_id=student_ada.id,
                    channel="in_app",
                    event_type="public.reply",
                    subject=f"New reply on {tkt_notes.public_reference}",
                    body="Prof. Donald Knuth posted a public reply on your scholarship stipend ticket.",
                    status="sent",
                    attempts=1,
                    sent_at=now_naive - timedelta(hours=3),
                    is_internal=False,
                ),
            ]
        )

        db.commit()

    engine.dispose()
    print(f"Disposable local demo database seeded at: {DEMO_DB_PATH}", flush=True)


if __name__ == "__main__":
    seed_demo_database()
    import uvicorn

    port = int(os.environ.get("DEMO_API_PORT", "8010"))
    uvicorn.run("app.main:app", host="127.0.0.1", port=port, log_level="info")
