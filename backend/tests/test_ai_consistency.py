"""Regression tests for ticket-grounded AI classification, routing, KB retrieval and response drafting.

Verifies that distinct university ticket topics:
1. Java OOP assignment -> Computer Science / academic_support
2. Password reset -> IT Services / account_access
3. Scholarship payment delay -> Scholarships & Financial Aid / financial_aid
4. Transcript verification -> Registry / student_records

produce distinct, ticket-grounded classifications, department/staff routing
recommendations, approved knowledge citations, and consistent response drafts
while preserving the human approval gate and real OpenAI provider path.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib

from sqlalchemy import func, select

from app.agents.services import agent_service
from app.agents.services.demo_llm import is_demo_api_key, make_ticket_grounded_llm
from app.agents.services.llm_service import LlmService, get_llm_service
from app.core.security import hash_password
from app.models import Department, KnowledgeDocument, Message, Ticket, TicketAiAnalysis, User
from app.services import byok


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _seed_four_departments_and_kbs(db_session, users) -> dict[str, Department]:
    """Ensure all four target university departments and approved KB policies exist."""
    now_utc = datetime.now(timezone.utc)
    admin = users["admin"]

    def _upsert_dept(name: str, description: str) -> Department:
        dept = db_session.scalar(select(Department).where(Department.name == name))
        if dept is None:
            dept = Department(name=name, description=description, is_active=True)
            db_session.add(dept)
            db_session.flush()
        else:
            dept.description = description
            dept.is_active = True
        return dept

    dept_cs = _upsert_dept(
        "Computer Science",
        "Computer Science coursework, Java programming assignment, object-oriented "
        "programming OOP concepts, classes, objects, inheritance, data structures, "
        "algorithm lab, compiler exam, software engineering grading rubric",
    )
    dept_it = _upsert_dept(
        "IT Services",
        "Technology support, student portal password reset, account access recovery, "
        "campus Wi-Fi, LMS portal login, VPN access, university email account MFA reset",
    )
    dept_fin = _upsert_dept(
        "Scholarships & Financial Aid",
        "Scholarships, financial aid, scholarship payment delay, tuition fee waiver, "
        "stipend disbursement, grant application, merit award documents",
    )
    dept_reg = _upsert_dept(
        "Registry",
        "Student records, academic transcript verification, official transcript, "
        "enrollment verification, semester registration, degree audit, medical deferral",
    )

    # Ensure an active CS instructor exists for CS staff recommendation verification
    cs_staff = db_session.scalar(
        select(User).where(User.email == "cs.instructor@university.edu")
    )
    if cs_staff is None:
        cs_staff = User(
            full_name="Dr. Grace Hopper (CS Instructor)",
            email="cs.instructor@university.edu",
            password_hash=hash_password("StrongPass1"),
            role="staff",
            department_id=dept_cs.id,
            is_active=True,
        )
        db_session.add(cs_staff)
        db_session.flush()

    kb_specs = [
        (
            "KB-CS-101",
            "CS Programming Assignment & Regrade Policy",
            dept_cs.id,
            (
                "Computer Science Assessment & Grading Rubric Policy (KB-CS-101):\n"
                "1. All programming assignments are evaluated against automated unit tests (60%), "
                "code architecture & complexity analysis (25%), and documentation (15%).\n"
                "2. Students may request a formal rubric breakdown or regrade within 7 calendar days."
            ),
        ),
        (
            "KB-CS-102",
            "CS Java & Object-Oriented Programming (OOP) Coursework Support Policy",
            dept_cs.id,
            (
                "Computer Science Java & Object-Oriented Programming (OOP) Coursework Support Policy (KB-CS-102):\n"
                "1. Students seeking help understanding Java programming assignments and core object-oriented "
                "programming (OOP) concepts—including classes, objects, constructors, encapsulation, inheritance, "
                "and polymorphism—are assigned to an available Computer Science instructor for academic guidance.\n"
                "2. Assigned Computer Science instructors provide 1-on-1 concept walkthroughs, starter-code reviews, "
                "and debugging guidance during weekly CS lab consultation hours or via ticket reply within 1 business day.\n"
                "3. Students should share the specific Java class or inheritance hierarchy they are working on so the "
                "assigned instructor can provide targeted OOP examples and explanations."
            ),
        ),
        (
            "KB-IT-401",
            "IT Services Student Portal Account Access & Password Reset Policy",
            dept_it.id,
            (
                "IT Services Student Portal Account Access & Password Reset Policy (KB-IT-401):\n"
                "1. Students who cannot sign in to the student portal or LMS due to a forgotten password or expired "
                "credentials can initiate an immediate password reset through the IT Self-Service Portal.\n"
                "2. If an account is locked after repeated login attempts or requires an MFA reset, IT Services Helpdesk "
                "verifies the student's university ID and issues a temporary access reset within 2 business hours."
            ),
        ),
        (
            "KB-FIN-301",
            "Merit Scholarship & Stipend Disbursement Policy",
            dept_fin.id,
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
        (
            "KB-REG-201",
            "Registry Transcript & Fellowship Verification Policy",
            dept_reg.id,
            (
                "Official Academic Transcript & Verification Policy (KB-REG-201):\n"
                "1. Standard official transcript verification takes 2 business days.\n"
                "2. Expedited graduate fellowship or scholarship verifications are processed within "
                "24 hours by the Registry Office upon uploading the fellowship reference letter."
            ),
        ),
    ]

    for source_key, title, dept_id, text in kb_specs:
        existing = db_session.scalar(
            select(KnowledgeDocument).where(KnowledgeDocument.source_key == source_key)
        )
        if existing is None:
            db_session.add(
                KnowledgeDocument(
                    title=title,
                    source_key=source_key,
                    version=1,
                    source_type="text",
                    checksum=_sha256(text),
                    content_text=text,
                    department_id=dept_id,
                    uploaded_by_id=admin.id,
                    approved_by_id=admin.id,
                    approved_at=now_utc - timedelta(days=5),
                    is_approved=True,
                    is_active=True,
                )
            )
    db_session.commit()
    return {
        "cs": dept_cs,
        "it": dept_it,
        "finance": dept_fin,
        "registry": dept_reg,
    }


def _create_ticket(
    db_session,
    *,
    student_id: int,
    assigned_to: int,
    department_id: int,
    public_reference: str,
    subject: str,
    description: str,
    category: str = "general",
    priority: str = "normal",
) -> Ticket:
    ticket = Ticket(
        public_reference=public_reference,
        subject=subject,
        description=description,
        category=category,
        priority=priority,
        status="assigned",
        student_id=student_id,
        assigned_to=assigned_to,
        department_id=department_id,
        channel="web",
        auto_routed=True,
    )
    db_session.add(ticket)
    db_session.commit()
    db_session.refresh(ticket)
    return ticket


def test_four_distinct_tickets_produce_consistent_grounded_classifications_and_drafts(
    db_session, users
):
    """Regression test across Java OOP, Password Reset, Scholarship Delay and Transcript Verification."""
    depts = _seed_four_departments_and_kbs(db_session, users)
    operator = users["staff"]
    byok.save_api_key(
        db_session,
        operator.id,
        "sk-local-test-operator-grounded-key-1234",
        validator=lambda _: True,
    )

    # 1. Java OOP assignment (exact TKT-7FA230F0 scenario)
    tkt_java = _create_ticket(
        db_session,
        student_id=users["student"].id,
        assigned_to=operator.id,
        department_id=depts["cs"].id,
        public_reference="TKT-7FA230F0",
        subject="Question about Java programming assignment",
        description=(
            "I need help understanding my Java programming assignment. I am facing "
            "difficulty with object-oriented programming concepts, especially classes, "
            "objects, and inheritance. Please review my query and assign it to an "
            "available Computer Science instructor who can guide me."
        ),
        category="Academic Support",
    )

    # 2. Password reset -> IT Services / account_access
    tkt_password = _create_ticket(
        db_session,
        student_id=users["student"].id,
        assigned_to=operator.id,
        department_id=depts["it"].id,
        public_reference="TKT-REG-IT01",
        subject="Locked out of student portal and need password reset",
        description=(
            "I cannot sign in to the university student portal because my password "
            "expired and my account is locked. Please help me reset my password and "
            "restore account access."
        ),
        category="Account Access",
    )

    # 3. Scholarship payment delay -> Scholarships & Financial Aid / financial_aid
    tkt_scholarship = _create_ticket(
        db_session,
        student_id=users["student"].id,
        assigned_to=operator.id,
        department_id=depts["finance"].id,
        public_reference="TKT-REG-FIN1",
        subject="Merit scholarship stipend payment delay",
        description=(
            "My merit scholarship stipend disbursement is delayed past week 3 even "
            "though my GPA is above 3.50. Could Scholarships and Financial Aid check "
            "why my payment is delayed and what form is required?"
        ),
        category="Financial Aid",
    )

    # 4. Transcript verification -> Registry / student_records
    tkt_transcript = _create_ticket(
        db_session,
        student_id=users["student"].id,
        assigned_to=operator.id,
        department_id=depts["registry"].id,
        public_reference="TKT-REG-TRN1",
        subject="Official academic transcript verification for graduate fellowship",
        description=(
            "I need an official academic transcript verification and enrollment "
            "confirmation processed by the Registry Office for my graduate fellowship "
            "application deadline."
        ),
        category="Student Records",
    )

    res_java = agent_service.run_ticket_analysis(db_session, tkt_java.id, operator)
    res_pw = agent_service.run_ticket_analysis(db_session, tkt_password.id, operator)
    res_fin = agent_service.run_ticket_analysis(db_session, tkt_scholarship.id, operator)
    res_reg = agent_service.run_ticket_analysis(db_session, tkt_transcript.id, operator)

    # --- 1. Verify Java OOP assignment (TKT-7FA230F0) ---
    assert res_java.status == "completed"
    assert res_java.classification is not None
    assert res_java.classification["category"] == "academic_support"
    assert res_java.classification["intent"] == "request_java_oop_academic_guidance"
    assert res_java.classification["intent"] != "request_password_reset_help"
    assert "password" not in " ".join(res_java.classification["entities"]).lower()
    assert "password" not in (res_java.classification.get("rationale") or "").lower()
    assert any(
        term in [e.lower() for e in res_java.classification["entities"]]
        for term in ("java", "oop", "object-oriented programming", "classes", "inheritance")
    )
    assert res_java.department_recommendation is not None
    assert res_java.department_recommendation["department_id"] == depts["cs"].id
    assert res_java.department_recommendation["department_name"] == "Computer Science"
    assert "account access" not in (res_java.department_recommendation.get("reason") or "").lower()
    assert res_java.no_evidence is False
    assert len(res_java.knowledge_sources) == 1
    assert "OOP" in res_java.knowledge_sources[0]["title"]
    assert res_java.draft is not None
    java_body = res_java.draft["body"].lower()
    assert "java" in java_body
    assert "inheritance" in java_body and "classes" in java_body
    assert "60%" not in java_body  # Not the grading rubric policy!
    assert res_java.validation is not None and res_java.validation["passed"] is True
    assert res_java.approved_message_id is None
    assert res_java.draft["needs_staff_review"] is True

    # --- 2. Verify Password Reset ---
    assert res_pw.status == "completed"
    assert res_pw.classification is not None
    assert res_pw.classification["category"] == "account_access"
    assert res_pw.classification["intent"] == "request_password_reset_help"
    assert res_pw.department_recommendation is not None
    assert res_pw.department_recommendation["department_id"] == depts["it"].id
    assert res_pw.department_recommendation["department_name"] == "IT Services"
    assert res_pw.no_evidence is False
    assert len(res_pw.knowledge_sources) == 1
    assert "Password Reset" in res_pw.knowledge_sources[0]["title"]
    assert res_pw.draft is not None
    pw_body = res_pw.draft["body"].lower()
    assert "password reset" in pw_body and "student portal" in pw_body
    assert "java" not in pw_body
    assert res_pw.validation is not None and res_pw.validation["passed"] is True
    assert res_pw.approved_message_id is None

    # --- 3. Verify Scholarship Payment Delay ---
    assert res_fin.status == "completed"
    assert res_fin.classification is not None
    assert res_fin.classification["category"] == "financial_aid"
    assert res_fin.classification["intent"] == "report_scholarship_payment_delay"
    assert res_fin.department_recommendation is not None
    assert res_fin.department_recommendation["department_id"] == depts["finance"].id
    assert res_fin.department_recommendation["department_name"] == "Scholarships & Financial Aid"
    assert res_fin.no_evidence is False
    assert len(res_fin.knowledge_sources) == 1
    assert "Scholarship" in res_fin.knowledge_sources[0]["title"]
    assert res_fin.draft is not None
    fin_body = res_fin.draft["body"].lower()
    assert "scholarship" in fin_body and "stipend" in fin_body
    assert "enrollment confirmation" in fin_body
    assert "java" not in fin_body and "password" not in fin_body
    assert res_fin.validation is not None and res_fin.validation["passed"] is True
    assert res_fin.approved_message_id is None

    # --- 4. Verify Transcript Verification ---
    assert res_reg.status == "completed"
    assert res_reg.classification is not None
    assert res_reg.classification["category"] == "student_records"
    assert res_reg.classification["intent"] == "request_transcript_verification"
    assert res_reg.department_recommendation is not None
    assert res_reg.department_recommendation["department_id"] == depts["registry"].id
    assert res_reg.department_recommendation["department_name"] == "Registry"
    assert res_reg.no_evidence is False
    assert len(res_reg.knowledge_sources) == 1
    assert "Transcript" in res_reg.knowledge_sources[0]["title"]
    assert res_reg.draft is not None
    reg_body = res_reg.draft["body"].lower()
    assert "transcript" in reg_body and "verification" in reg_body
    assert "2 business days" in reg_body or "24 hours" in reg_body
    assert "java" not in reg_body and "password" not in reg_body
    assert res_reg.validation is not None and res_reg.validation["passed"] is True
    assert res_reg.approved_message_id is None

    # --- 5. Cross-ticket distinctness and human approval gate check ---
    all_results = [res_java, res_pw, res_fin, res_reg]
    assert len({r.classification["intent"] for r in all_results}) == 4
    assert len({r.classification["category"] for r in all_results}) == 4
    assert len({r.department_recommendation["department_id"] for r in all_results}) == 4
    assert len({r.knowledge_sources[0]["source_id"] for r in all_results}) == 4
    assert len({r.draft["body"] for r in all_results}) == 4

    total_messages = db_session.scalar(select(func.count()).select_from(Message))
    assert total_messages == 0, "No AI draft may be auto-published without human approval"


def test_real_openai_path_and_demo_path_are_cleanly_separated():
    """Verify real OpenAI keys use live LlmService while sk-local-test-* keys use grounded demo client."""
    assert is_demo_api_key("sk-local-test-mock-key-grace-9876") is True
    assert is_demo_api_key("sk-demo-local-key-123456") is True
    assert is_demo_api_key("sk-proj-realOpenAiKeyExample123456789") is False
    assert is_demo_api_key("sk-test-key-for-user-a-1234567890") is False
    assert is_demo_api_key(None) is False

    demo_service = get_llm_service("sk-local-test-mock-key-grace-9876")
    assert isinstance(demo_service, LlmService)
    assert demo_service._client is not None

    real_service = get_llm_service("sk-proj-realOpenAiKeyExample123456789")
    assert isinstance(real_service, LlmService)
    assert real_service._client is None  # Lazily constructs real OpenAI SDK client

    grounded = make_ticket_grounded_llm()
    assert grounded.test_connection()["connected"] is True
