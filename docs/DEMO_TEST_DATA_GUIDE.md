# Disposable Demo Test Data Guide

**Project:** Smart Query Routing & Email Automation System  
**Document Date:** 2026-11-23  
**Seeder Implementation:** `backend/demo_server.py` (invoked automatically by `scripts/start_local_demo.ps1`)  
**Database Location:** `frontend-next/.e2e/demo_local_test.db` (disposable local SQLite database; gitignored)  
**Attachment Storage:** `frontend-next/.e2e/demo_attachments/` (disposable local folder; gitignored)

> **Safety Notice:** All credentials, accounts, tickets, and tokens in this document are **disposable local demonstration fixtures**. They exist only inside the local SQLite file created by `backend/demo_server.py` and are never used in production.

---

## 1. Disposable Demo User Accounts

All seeded demo accounts share the same disposable local password:

- **Password for all seeded demo accounts:** `LocalTestDemo123!`

| Role | Full Name | Email | Department | Special Demo State |
| --- | --- | --- | --- | --- |
| **Student 1** | Ada Lovelace (Student) | `demo.student@university.edu` | *None (Student)* | Primary demo student; owns `TKT-DEMO0001`, `TKT-DEMO0002`, `TKT-DEMO0004` |
| **Student 2** | Alan Turing (Student 2) | `demo.student2@university.edu` | *None (Student)* | Isolation test student; owns private ticket `TKT-DEMO0003` (ID `3`) |
| **Staff (Instructor 1)** | Dr. Grace Hopper (CS Instructor) | `demo.staff.cs1@university.edu` | Computer Science | Eligible active CS instructor; auto-assigned `TKT-DEMO0001` |
| **Staff (Instructor 2)** | Dr. Edsger Dijkstra (CS Instructor - On Leave) | `demo.staff.cs2@university.edu` | Computer Science | **On Active Leave** (`now - 2d` to `now + 5d`); excluded from auto-routing; triggers auto-reply if manually assigned |
| **Staff (Registry)** | Prof. Margaret Hamilton (Registry Staff) | `demo.staff.reg@university.edu` | Registry | Eligible Registry instructor; assigned overdue ticket `TKT-DEMO0002` |
| **Staff (Scholarships)** | Prof. Donald Knuth (Scholarships Staff) | `demo.staff.fin@university.edu` | Scholarships & Financial Aid | Eligible Scholarships staff; assigned `TKT-DEMO0004` |
| **HOD (CS)** | Dr. Barbara Liskov (CS HOD) | `demo.hod.cs@university.edu` | Computer Science | Department-scoped manager for Computer Science |
| **HOD (Registry)** | Dr. Tim Berners-Lee (Registry HOD) | `demo.hod.reg@university.edu` | Registry | Department-scoped manager for Registry |
| **System Admin** | Prof. John McCarthy (System Admin) | `demo.admin@university.edu` | *All Departments* | Global system administrator (audit log, SLA sweep, analytics, departments, knowledge approval) |

*(Note: For automated Playwright E2E tests launched via `npm run test:e2e`, `backend/e2e_server.py` seeds a separate disposable database `frontend-next/.e2e/e2e.db` with `e2e.student@university.edu`, `e2e.student2@university.edu`, `e2e.staff@university.edu`, and `e2e.admin@university.edu`).*

---

## 2. Seeded University Departments & Auto-Routing Keywords

`app/services/auto_routing.py` scores incoming query tokens deterministically (+3 for department name matches, +2 for department description matches; minimum score 2):

| ID | Department Name | Persisted Description (Routing Keywords) | Eligible Active Staff (Not on Leave) |
| --- | --- | --- | --- |
| `1` | **Computer Science** | `Computer Science coursework, programming assignment, data structures, algorithm lab, compiler exam, software engineering grading rubric` | `Dr. Grace Hopper` (`Dr. Edsger Dijkstra` excluded due to active leave) |
| `2` | **Registry** | `Student records, academic transcript, enrollment verification, semester registration, degree audit, medical deferral` | `Prof. Margaret Hamilton` |
| `3` | **Scholarships & Financial Aid** | `Scholarships, financial aid, tuition fee waiver, stipend disbursement, grant application, merit award documents` | `Prof. Donald Knuth` |
| `4` | **IT Services** | `Technology support, campus Wi-Fi, LMS portal login, VPN access, university email account MFA reset` | *None seeded* (demonstrates `ticket.instructor_routing_skipped` with `reason: "no_eligible_instructor"`, leaving ticket in `New` for HOD/Admin triage) |

### Sample Copy-Paste Queries for Live Auto-Routing Demos

1. **Routes to Computer Science & assigns Dr. Grace Hopper (excluding Dr. Dijkstra on leave):**
   - **Subject:** `Data structures programming assignment grading rubric inquiry`
   - **Description:** `Could you clarify how the algorithm lab complexity analysis is scored on our programming assignment?`
2. **Routes to Registry & assigns Prof. Margaret Hamilton:**
   - **Subject:** `Official academic transcript and enrollment verification request`
   - **Description:** `I need an enrollment verification letter and official academic transcript for my degree audit.`
3. **Routes to Scholarships & Financial Aid & assigns Prof. Donald Knuth:**
   - **Subject:** `Tuition fee waiver and merit scholarship stipend disbursement`
   - **Description:** `When will the financial aid stipend disbursement appear on my semester billing statement?`
4. **Routes to IT Services & demonstrates graceful fallback when no instructor is available:**
   - **Subject:** `Campus Wi-Fi and LMS portal login MFA reset`
   - **Description:** `I cannot sign in to the LMS portal or connect to campus VPN after changing my phone.`

---

## 3. Seeded Tickets & Demonstration Scenarios

| Ticket ID | Public Reference | Owner (Student) | Department | Assignee | Initial Status | Created Age | Purpose in Demonstration |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `1` | `TKT-DEMO0001` | Ada Lovelace | Computer Science | Dr. Grace Hopper | `assigned` | 2 hours ago | Has a **pre-computed grounded AI analysis & unapproved draft** citing `KB-CS-101`. Used to demonstrate the AI Assist panel and Human Approval Gate (`Approve & post reply`) offline without needing a paid OpenAI key. |
| `2` | `TKT-DEMO0002` | Ada Lovelace | Registry | Prof. Margaret Hamilton | `in_progress` | **30 hours ago** | Exceeds the 24-hour `SLA_HOURS` window (`is_escalated=False`). Used to demonstrate deterministic 24h SLA auto-escalation (`POST /api/v1/tickets/escalation/sweep` or `/run`) and repeat-safe idempotency.Also has no AI analysis yet, so clicking `Analyze this query` demonstrates the fail-closed BYOK guard (`402 ai_personal_key_required`). |
| `3` | `TKT-DEMO0003` | **Alan Turing** | Registry | *Unassigned* | `new` | 4 hours ago | Belongs to `demo.student2@university.edu`. Used to demonstrate horizontal ticket isolation: when `demo.student@university.edu` visits `/tickets/3`, the backend returns `404 Not Found`. |
| `4` | `TKT-DEMO0004` | Ada Lovelace | Scholarships & Financial Aid | Prof. Donald Knuth | `waiting_for_student` | 5 hours ago | Contains **one public staff reply** and **one internal staff note** (`is_internal=True`). Used to demonstrate internal-note privacy: staff/HOD/admin see both messages, while the student sees only the public reply. |

---

## 4. Seeded Approved Knowledge Base Documents

| Source Key | Title | Department | Status | Summary |
| --- | --- | --- | --- | --- |
| `KB-CS-101` | CS Programming Assignment & Regrade Policy | Computer Science | `Approved` & `Active` | Defines 60% unit tests / 25% architecture / 15% documentation weighting and 7-day regrade window. Cited in `TKT-DEMO0001`'s AI draft. |
| `KB-REG-201` | Registry Transcript & Fellowship Verification Policy | Registry | `Approved` & `Active` | Defines 2-day standard transcript processing and 24-hour expedited graduate fellowship verification. |
| `KB-FIN-301` | Merit Scholarship & Stipend Disbursement Policy | Scholarships & Financial Aid | `Approved` & `Active` | Defines 3.50 GPA requirement, signed enrollment confirmation upload, and Week 3 stipend disbursement. |

---

## 5. Seeded Local Webhook & Cron Tokens (Disposable Demo Only)

When running `backend/demo_server.py` (via `scripts/start_local_demo.ps1`), the following local-only tokens are configured in memory for demonstrating the protected operational and inbound webhook endpoints:

- **SLA Escalation Cron Header (`X-Cron-Secret`):** `local-test-demo-cron-secret-not-for-production`
- **Inbound Email/WhatsApp Webhook Header (`X-Intake-Token`):** `local-test-demo-intake-token-not-for-production`

### Resetting the Demo Database to a Clean State

Every time `powershell -ExecutionPolicy Bypass -File .\scripts\start_local_demo.ps1` is started (after stopping with `-Stop`), `backend/demo_server.py` drops and recreates all tables in `frontend-next/.e2e/demo_local_test.db`, restoring the exact initial state above in less than 2 seconds.
