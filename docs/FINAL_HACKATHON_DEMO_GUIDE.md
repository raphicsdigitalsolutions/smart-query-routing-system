# Final University & Hackathon Demonstration Guide

**Project:** Smart Query Routing & Email Automation System (University Intelligent Communication Hub)  
**Document Date:** 2026-11-23  
**Demonstration Scope:** Reproducible local/offline full-stack demonstration using disposable local test data (`backend/demo_server.py` + `scripts/start_local_demo.ps1`).  
**Honesty & Evidence Policy:** This guide distinguishes strictly between **locally verified features** (executed live in the browser against the local FastAPI backend and disposable SQLite database) and **mocked / unverified external provider integrations** (Google OAuth2, SMTP email, Meta WhatsApp Cloud API, and live paid OpenAI inference). No live external provider integration is claimed where only offline or mocked verification exists.

---

## 0. Starting and Stopping the Local Demonstration

### Start the Local Demo Stack

From a Windows PowerShell terminal at the repository root (`C:\Users\user\OneDrive\Desktop\SmartQuerySystem`):

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start_local_demo.ps1
```

What this script does safely:
1. Checks Python (`backend\.venv`), Node.js/npm, Docker CLI availability, and Docker/Compose configuration files.
2. Verifies that all 16 required environment variables are documented in `.env.example` and `backend/.env.example` **without printing any secret values**.
3. Ensures the Next.js production build (`frontend-next/.next/BUILD_ID`) exists.
4. Starts `backend/demo_server.py` on `http://127.0.0.1:8010` (or the next free port if occupied, avoiding conflicts with any existing service on port `8000`) using an isolated, disposable SQLite database (`frontend-next/.e2e/demo_local_test.db`) — **never connecting to any production or hosted database**.
5. Starts the Next.js BFF/UI server on `http://127.0.0.1:3000` configured with `API_BASE_URL=http://127.0.0.1:8010/api/v1`.
6. Verifies `/health`, `/api/v1/status`, `/api/v1/status/database`, `/api/health`, `/login`, and an end-to-end student login via `POST /api/auth/login`.

### Stop the Local Demo Stack

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start_local_demo.ps1 -Stop
```

---

## 1. Application Overview

- **User Role:** Unauthenticated Visitor / Evaluator
- **Exact Action:**
  1. Run `powershell -ExecutionPolicy Bypass -File .\scripts\start_local_demo.ps1`.
  2. Open `http://127.0.0.1:3000/login` in Chrome or Edge.
  3. Open `http://127.0.0.1:3000/api/health` and `http://127.0.0.1:8010/docs` in secondary tabs.
- **Expected Output:**
  - The terminal prints `[PASS]` for Backend Liveness (`/health`), Backend API Status (`/api/v1/status`), Backend Database Readiness (`/api/v1/status/database`), Frontend BFF Health (`/api/health`), and Frontend UI (`/login`).
  - `http://127.0.0.1:3000/login` displays the **Smart Query Routing System** sign-in card (`Welcome back`) with email/password fields and link to student self-registration.
  - `http://127.0.0.1:3000/api/health` returns `{"status":"ok",...}` confirming the Next.js BFF reaches the FastAPI backend.
  - `http://127.0.0.1:8010/docs` renders the interactive OpenAPI 3.1 specification (41 paths across authentication, tickets, AI, knowledge, leave, notifications, integrations, analytics, reports, announcements, and audit).
- **Screenshot / Evidence Required:**
  - `demo-01-overview-health.png`: Terminal output showing all 5 `[PASS]` health checks alongside the browser showing `/login` and `/api/health`.

---

## 2. Student Login and Ticket Creation (FR-01, FR-02)

- **User Role:** Student (`Ada Lovelace` — `demo.student@university.edu` / `LocalTestDemo123!`)
- **Exact Action:**
  1. On `http://127.0.0.1:3000/login`, enter Email `demo.student@university.edu` and Password `LocalTestDemo123!`, then click **Sign in**.
  2. Observe the Student Workspace (`/student`), active university announcements, and existing student tickets (`TKT-DEMO0001`, `TKT-DEMO0002`, `TKT-DEMO0004`).
  3. In the **Submit a new query** form:
     - **Subject:** `Need help with data structures programming assignment compiler error`
     - **Description:** `My programming assignment compiles locally but fails the automated grading rubric check in the algorithm lab. Please advise.`
     - **Priority:** `Normal`
     - **Department:** Leave on **Auto-route (recommended)** (or select automatic routing).
  4. Click **Submit query**.
- **Expected Output:**
  - The BFF sets an `HttpOnly` session cookie (`smartquery_session`) and CSRF cookie (`smartquery_csrf`) — no JWT is stored in `localStorage` or `sessionStorage`.
  - A status banner confirms: `TKT-XXXXXXXX submitted successfully`.
  - The new ticket immediately appears at the top of the **My queries** table with a unique `TKT-XXXXXXXX` reference ID.
- **Screenshot / Evidence Required:**
  - `demo-02-student-ticket-created.png`: Student workspace showing the `TKT-XXXXXXXX submitted successfully` banner and the newly created ticket row.

---

## 3. Automatic Department Routing (FR-04)

- **User Role:** Student (`demo.student@university.edu`) or System Admin (`demo.admin@university.edu`)
- **Exact Action:**
  1. Click the newly created ticket (`Need help with data structures programming assignment compiler error`) from the student ticket table to open `/tickets/<id>`.
  2. Inspect the **Department**, **Category**, and **Status** fields on the ticket detail card.
- **Expected Output:**
  - **Department** is automatically resolved to **Computer Science** by `app/services/auto_routing.py` using deterministic keyword scoring against the persisted department name and description (`programming`, `assignment`, `algorithm`, `grading`, `rubric`).
  - **Category** is populated from the matched keywords (`algorithm` or `assignment`).
  - No paid LLM call is required for intake routing; deterministic routing works offline with zero external latency.
- **Screenshot / Evidence Required:**
  - `demo-03-auto-department-routing.png`: Ticket detail header and metadata showing `Department: Computer Science`, matched category pill, and `Auto-routed` history entry.

---

## 4. Instructor Assignment (FR-04b)

- **User Role:** Student (`demo.student@university.edu`) viewing Ticket Detail `/tickets/<id>`
- **Exact Action:**
  1. On the same newly created Computer Science ticket (`/tickets/<id>`), inspect the **Assigned to** field and scroll down to the **Ticket history** timeline.
- **Expected Output:**
  - **Status** automatically transitioned from `New` to `Assigned` at creation time.
  - **Assigned to** displays **`Dr. Grace Hopper (CS Instructor)`**.
  - The **Ticket history** section shows:
    - Status change: `New → Assigned` (`Automatically routed to an available instructor`).
    - Assignment record: `Assigned to Dr. Grace Hopper (CS Instructor)`.
  - The deterministic selector (`app/services/instructor_routing.py`) chose `Dr. Grace Hopper` using the auditable rule `least_open_workload_then_full_name_then_id` among eligible active `staff` in Computer Science (never auto-assigning HOD or Admin accounts).
- **Screenshot / Evidence Required:**
  - `demo-04-instructor-auto-assignment.png`: Ticket detail showing `Assigned to: Dr. Grace Hopper (CS Instructor)` and the status/assignment history timeline.

---

## 5. Instructor Leave Handling (FR-13)

- **User Role:** Computer Science HOD (`Dr. Barbara Liskov` — `demo.hod.cs@university.edu` / `LocalTestDemo123!`)
- **Exact Action:**
  1. Sign out and sign in as `demo.hod.cs@university.edu` (`LocalTestDemo123!`).
  2. Navigate to **Leave** (`/leave`) in the sidebar to inspect active department leave windows.
  3. Confirm that **`Dr. Edsger Dijkstra (CS Instructor - On Leave)`** (`demo.staff.cs2@university.edu`) has an active leave window (`Attending ACM Symposium on Operating Systems Principles`) with an automated absence reply configured.
  4. Navigate to the Computer Science ticket (`TKT-DEMO0001` or the newly submitted CS ticket) at `/tickets/1`.
  5. Verify that automatic routing **excluded** `Dr. Edsger Dijkstra` because of his active leave window and assigned `Dr. Grace Hopper` instead.
  6. In the right-hand **Workflow controls** panel, manually reassign the ticket to **`Dr. Edsger Dijkstra (CS Instructor - On Leave)`** to test manual-assignment auto-reply behavior.
- **Expected Output:**
  - On `/leave`, `Dr. Edsger Dijkstra`'s active leave window and auto-reply message are displayed.
  - During automatic routing (Step 4), `Dr. Edsger Dijkstra` was skipped (`excluded_on_leave_count: 1`).
  - Upon manual assignment by the HOD (Step 6), the backend immediately posts a public message on the ticket from `Dr. Edsger Dijkstra` containing his configured absence auto-reply (`"Thank you for your query. I am currently on approved academic leave attending the ACM Symposium..."`) and records an `assignment.auto_reply` notification for the student.
- **Screenshot / Evidence Required:**
  - `demo-05a-leave-window-list.png`: The `/leave` page showing `Dr. Edsger Dijkstra`'s active leave window.
  - `demo-05b-leave-manual-assign-autoreply.png`: Ticket conversation showing the automatic public absence reply posted immediately after manual assignment to the on-leave instructor.

---

## 6. Instructor Response and Approval Workflow (FR-05, D-DATA-04, D-DATA-05)

- **User Role:** Computer Science Instructor (`Dr. Grace Hopper` — `demo.staff.cs1@university.edu` / `LocalTestDemo123!`)
- **Exact Action:**
  1. Sign in as `demo.staff.cs1@university.edu` (`LocalTestDemo123!`) and open assigned ticket `TKT-DEMO0001` (`/tickets/1`).
  2. Inspect the **AI assistance** panel on `/tickets/1`, which displays the grounded AI analysis (Version 1), classification (`grading_policy_inquiry`, `94%` confidence), cited approved knowledge source (`KB-CS-101`: *CS Programming Assignment & Regrade Policy*), validation status (`Validation passed`), and the response draft labeled **`Not public until approved`**.
  3. Click **Approve & post reply** in the AI assistance panel.
  4. Next, in the **Conversation** composer below, check **Internal staff note (hidden from student)**, type `"INTERNAL NOTE: Checked student's Git commit hash; unit test 4 timed out due to O(n^2) loop."`, and click **Add internal note**.
- **Expected Output:**
  - Before clicking **Approve & post reply**, the AI draft is completely invisible to the student and no email/notification is sent.
  - Clicking **Approve & post reply** calls `POST /api/v1/ai/tickets/1/approve-draft`, publishes the cited reply as an official public message in the conversation timeline, marks the AI badge **`Approved & posted`**, updates `first_response_at`, and writes both `ai.draft_approved` and `message.created` audit entries.
  - Clicking **Approve & post reply** a second time is idempotent (`already_approved: true`) and never duplicates the message.
  - The internal staff note appears in the staff conversation view with an **Internal note** badge and is **never** sent to notifications or returned to student queries.
- **Screenshot / Evidence Required:**
  - `demo-06a-ai-draft-before-approval.png`: AI assistance panel showing `Human approval required`, `KB-CS-101` citation, and `Not public until approved`.
  - `demo-06b-ai-draft-approved-and-internal-note.png`: Conversation timeline showing the newly approved public reply alongside the staff-only internal note.

---

## 7. HOD / Admin Dashboard, Analytics, Broadcasts, and Reports (FR-09, FR-10, FR-11, FR-12)

- **User Role:** System Admin (`Prof. John McCarthy` — `demo.admin@university.edu` / `LocalTestDemo123!`) and CS HOD (`Dr. Barbara Liskov` — `demo.hod.cs@university.edu`)
- **Exact Action:**
  1. Sign in as `demo.admin@university.edu` (`LocalTestDemo123!`).
  2. Visit **Admin console** (`/admin`) to review department management and system-wide ticket oversight.
  3. Visit **Analytics** (`/analytics`) to view Recharts visualizations (ticket volume by status, priority, department, and SLA metrics) and click the **Export PDF** and **Export Excel (.xlsx)** buttons.
  4. Visit **Announcements** (`/announcements`) to view the active broadcast (`Spring Semester Scholarship Verification & CS Lab Deadlines`) and create a new broadcast targeted to `student`.
  5. Visit **Knowledge** (`/knowledge`) to view the governed knowledge documents (`KB-CS-101`, `KB-REG-201`, `KB-FIN-301`) and their approval states.
- **Expected Output:**
  - `/analytics` renders real aggregated counts from the database and downloads valid binary `.pdf` (ReportLab) and `.xlsx` (OpenPyXL) report files via the BFF streaming endpoint.
  - `/announcements` creates and publishes the announcement immediately to the selected role audience.
  - `/knowledge` shows versioned, checksummed policy documents with explicit `Approved` badges.
  - When signed in as HOD (`demo.hod.cs@university.edu`), ticket lists and analytics are automatically scoped to **Computer Science** only, and any HOD ticket mutation is flagged `is_override: true` in the audit log.
- **Screenshot / Evidence Required:**
  - `demo-07a-admin-analytics-and-exports.png`: Analytics dashboard charts and downloaded PDF/XLSX report files.
  - `demo-07b-announcements-and-knowledge.png`: Announcements management and Approved Knowledge repository views.

---

## 8. Ticket Status Tracking & Conditional Polling (FR-06)

- **User Role:** Student (`demo.student@university.edu`) in Browser Window A + Admin/Staff (`demo.admin@university.edu`) in Browser Window B (or API call)
- **Exact Action:**
  1. In Browser Window A (signed in as `demo.student@university.edu`), open `/tickets/1` (`TKT-DEMO0001`).
  2. Confirm the header displays the green **`Live updates`** indicator (`aria-label="Live status updates enabled"`).
  3. Open browser DevTools → Network tab and filter by `updates`. Observe periodic `GET /api/backend/tickets/1/updates` requests returning `200 OK` (initial snapshot with `ETag: "tkt-..."`) followed by `304 Not Modified` when nothing has changed.
  4. In Browser Window B (or via API as Admin/Staff), update Ticket 1's status to **`In progress`** (or **`Resolved`** with a required resolution summary: `"Provided full grading rubric breakdown and unit test logs."`).
  5. Watch Browser Window A without refreshing the page.
- **Expected Output:**
  - Within ~15 seconds (the `useTicketStatusPolling` interval), the next conditional `GET /tickets/1/updates` detects a new `ETag`, returns `200 OK` with the updated snapshot, and automatically refreshes the ticket status pill and timeline in Browser Window A without a manual page reload.
  - **Architectural honesty note:** This is implemented via lightweight conditional HTTP polling (`ETag` / `304 Not Modified`), **not** WebSockets or Server-Sent Events (SSE).
  - Attempting to transition a ticket to `resolved` or `closed` without a `resolution_summary` is rejected by the backend with HTTP `400 resolution_summary_required`.
- **Screenshot / Evidence Required:**
  - `demo-08-live-polling-status-update.png`: Student ticket detail view showing `Live updates`, DevTools `ETag` / `304` -> `200` network trace, and the updated status pill.

---

## 9. System-Wide Audit Log (FR-14)

- **User Role:** System Admin (`demo.admin@university.edu` / `LocalTestDemo123!`)
- **Exact Action:**
  1. Sign in as `demo.admin@university.edu` and open **Audit log** (`/audit`) from the sidebar.
  2. Filter or inspect the chronological audit trail across the actions performed in Steps 2–8.
- **Expected Output:**
  - The audit table displays immutable database rows with timestamp, actor email, actor role, action identifier, entity type/ID, `is_override` flag, and structured JSON details:
    - `auth.login_succeeded` / `auth.login_failed` / `auth.registered` (never logging plaintext passwords or tokens)
    - `ticket.created`
    - `ticket.auto_routed` (with matched keywords)
    - `ticket.instructor_auto_assigned` (with workload and `excluded_on_leave_count`)
    - `ai.analysis_created` and `ai.draft_approved`
    - `message.created` (including `is_internal` and `auto_reply` flags)
    - `ticket.assigned`, `ticket.status_changed`, `ticket.escalated`, `ticket.escalated_automatically`
    - `leave.created` / `leave.updated` / `leave.deactivated`
  - HOD and Admin ticket overrides display an explicit **Override** indicator (`is_override: true`).
- **Screenshot / Evidence Required:**
  - `demo-09-admin-audit-log.png`: Admin `/audit` screen showing auth, auto-routing, instructor assignment, AI approval, and override events.

---

## 10. AI / BYOK Demonstration (FR-03, FR-05, D-SEC-01)

- **User Role:** Staff or Admin (`demo.staff.cs1@university.edu` or `demo.admin@university.edu`)
- **Exact Action:**
  1. Navigate to **Settings** (`/settings`) to inspect the **Personal OpenAI API Key (BYOK)** panel.
  2. Observe that the status is currently **`Not configured`** and that no global fallback key is active (`ALLOW_GLOBAL_OPENAI_FALLBACK=false`).
  3. Open Ticket 2 (`/tickets/2`, which does not have a pre-seeded AI analysis) and click **Analyze this query**.
  4. Observe the fail-closed BYOK security response.
  5. *(Optional if the evaluator supplies a disposable personal OpenAI key)*: Enter a key in `/settings` -> the backend validates it against OpenAI `models.list()`, encrypts it with Fernet (`BYOK_ENCRYPTION_KEY`), stores only the ciphertext and a masked hint (`sk-...XXXX`), and never returns the key in any API response.
- **Expected Output:**
  - Without a personal key configured, clicking **Analyze this query** fails closed with HTTP `402 Payment Required` (`code: "ai_personal_key_required"`) and displays the prompt: **`Add your personal AI key — AI assistance needs your own API key. No shared or administrator key is used.`**
  - Meanwhile, Ticket 1 (`/tickets/1`) demonstrates the complete persisted output of the 5-node bounded LangGraph pipeline (`classification → routing → knowledge_research → response_drafting → validation`) and its human approval gate without requiring live paid API calls during the offline presentation.
- **Screenshot / Evidence Required:**
  - `demo-10a-byok-settings-and-fail-closed.png`: The `/settings` BYOK card and the fail-closed `Add your personal AI key` notice when no personal key is stored.

---

## 11. Email and WhatsApp Mocked vs. Live Status (FR-02, FR-08)

- **User Role:** System Admin (`demo.admin@university.edu`) / API Evaluator
- **Exact Action:**
  1. Open `http://127.0.0.1:8010/api/v1/integrations/status` in the browser or query it with `Invoke-RestMethod http://127.0.0.1:8010/api/v1/integrations/status`.
  2. In the UI, navigate to **Notifications** (`/notifications`) while signed in as `demo.student@university.edu` or `demo.staff.cs1@university.edu`.
  3. Test the token-protected inbound email and WhatsApp intake adapters locally against the running demo server:
     ```powershell
     $headers = @{ "X-Intake-Token" = "local-test-demo-intake-token-not-for-production" }
     Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8010/api/v1/integrations/email/inbound" `
       -Headers $headers -ContentType "application/json" `
       -Body '{"student_email":"demo.student@university.edu","subject":"Inbound email scholarship inquiry","body":"Please confirm merit scholarship form deadline.","auto_route":true}'

     Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8010/api/v1/integrations/whatsapp/inbound" `
       -Headers $headers -ContentType "application/json" `
       -Body '{"student_email":"demo.student@university.edu","from_phone":"+15550109999","body":"Need help with algorithm lab programming assignment rubric","auto_route":true}'
     ```
- **Expected Output:**
  - `GET /api/v1/integrations/status` reports honestly:
    `{"smtp": false, "whatsapp": false, "google_oauth": false, "intake_webhook": true}`
  - **What is LIVE & VERIFIED locally:**
    - In-app notifications (`/notifications`) are persisted and displayed for every public event (`ticket.created`, `ticket.assigned`, `public.reply`, `assignment.auto_reply`, `ticket.escalated_automatically`, `ticket.resolved`, `ticket.closed`), with unread counters and mark-as-read functionality.
    - Outbound notification deduplication (10-minute idempotency window per `(ticket_id, event_type, recipient_user_id, channel)`), internal-note suppression, unapproved-draft suppression, and sanitized error handling (`safe_exception_summary`) are verified by `backend/tests/test_notifications.py`.
    - Inbound Email (`POST /api/v1/integrations/email/inbound`) and Inbound WhatsApp (`POST /api/v1/integrations/whatsapp/inbound`) token-gated webhooks create real tickets with `channel="email"` and `channel="whatsapp"` and trigger deterministic department/instructor auto-routing.
    - Meta WhatsApp GET webhook verification handshake (`GET /api/v1/integrations/whatsapp/webhook`) is implemented and unit-tested (`backend/tests/test_integrations.py`).
  - **What is MOCKED / NOT VERIFIED LIVE:**
    - Live outbound SMTP delivery to an external mail server and live Meta Cloud API WhatsApp delivery to a mobile handset require external provider credentials, domain SPF/DKIM/DMARC verification, and Meta Business verification, which are not enabled in the local demo environment.
- **Screenshot / Evidence Required:**
  - `demo-11-integrations-and-notifications.png`: Output of `/api/v1/integrations/status`, the inbound webhook PowerShell responses showing `channel: "email"` and `channel: "whatsapp"`, and the `/notifications` screen in the UI.

---

## 12. 24-Hour SLA Auto-Escalation Demonstration (FR-07)

- **User Role:** System Admin (`demo.admin@university.edu` / `LocalTestDemo123!`)
- **Exact Action:**
  1. In the UI as Admin (`demo.admin@university.edu`), open Ticket 2 (`TKT-DEMO0002` — `Urgent academic transcript verification for graduate fellowship`) at `/tickets/2`.
  2. Observe that `TKT-DEMO0002` was created 30 hours ago (> 24-hour `SLA_HOURS`), is in status `In progress`, and is currently **not escalated** (`is_escalated: false`).
  3. Trigger the deterministic SLA escalation sweep via the secret-protected cron endpoint (or Admin endpoint):
     ```powershell
     Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8010/api/v1/tickets/escalation/sweep" `
       -Headers @{ "X-Cron-Secret" = "local-test-demo-cron-secret-not-for-production" }
     ```
  4. Re-run the exact same command a second time to verify repeat-safety (idempotency).
  5. Observe `/tickets/2` in the browser (or refresh).
- **Expected Output:**
  - The first sweep call returns `{"scanned": 2, "escalated": 2}` (escalating the overdue tickets `TKT-DEMO0002` and any other ticket older than 24h, or `{"scanned": 1, "escalated": 1}` specifically for `TKT-DEMO0002` created 30h ago).
  - The second sweep call returns `{"scanned": 0, "escalated": 0}` — proving the sweep is repeat-safe and does not emit duplicate audit rows or duplicate notifications.
  - On `/tickets/2`, the red **`Escalated`** badge and flag icon appear, the status history shows `Automatically escalated after 24h SLA`, and the `/audit` log records `ticket.escalated_automatically`.
  - Calling `/api/v1/tickets/escalation/sweep` with a wrong `X-Cron-Secret` fails closed with HTTP `401 invalid_cron_secret`.
- **Screenshot / Evidence Required:**
  - `demo-12-sla-escalation-sweep.png`: PowerShell terminal showing first run (`escalated: 1`) and second run (`escalated: 0`), plus `/tickets/2` displaying the `Escalated` badge.

---

## 13. Security, Attachment Validation, and Role Isolation (D-RBAC-00, D-QA-00, D-SEC-05)

- **User Role:** Student 1 (`demo.student@university.edu` — `Ada Lovelace`) attempting unauthorized access to Student 2's ticket (`TKT-DEMO0003`, Ticket ID `3`, owned by `Alan Turing`) and Admin screens
- **Exact Action:**
  1. Sign in as `demo.student@university.edu` (`LocalTestDemo123!`).
  2. Attempt to navigate directly to Student 2's private ticket at `http://127.0.0.1:3000/tickets/3` (`TKT-DEMO0003` — `Private medical semester deferral request - Alan Turing`).
  3. Attempt to navigate directly to `http://127.0.0.1:3000/admin` and `http://127.0.0.1:3000/audit`.
  4. Open Student 1's own ticket `http://127.0.0.1:3000/tickets/4` (`TKT-DEMO0004`), where `Prof. Donald Knuth` posted both a public reply and an internal staff note.
  5. On `http://127.0.0.1:3000/tickets/4`, upload a valid `.txt` or `.pdf` attachment (`enrollment_confirmation.txt`), then attempt to upload a disallowed `.exe` or `.bat` file.
- **Expected Output:**
  - **Horizontal Ticket Isolation (`D-QA-00`):** Opening `/tickets/3` returns HTTP `404 Not Found` from the backend (`Ticket unavailable` in the UI). Neither the subject (`Private medical semester deferral request - Alan Turing`) nor the reference (`TKT-DEMO0003`) is leaked.
  - **Vertical Role Isolation (`D-RBAC-00`):** Opening `/admin` or `/audit` displays `Access restricted — Backend authorization remains the final authority`, and direct backend requests to `/api/v1/audit` or `/api/v1/analytics` with a student token return HTTP `403 Forbidden`.
  - **Internal-Note Privacy (`D-DATA-04`):** On `/tickets/4`, `Ada Lovelace` sees `Prof. Donald Knuth`'s public reply (`Hello Ada, per policy KB-FIN-301...`) but **never** sees the internal note (`INTERNAL STAFF NOTE: Verified Ada's 3.85 GPA...`) in the UI or in the `/api/backend/tickets/4/messages` network payload.
  - **Attachment Validation (`D-SEC-05`):** The valid UTF-8 `.txt` / `%PDF` `.pdf` file (<= 5 MiB) is accepted, checksummed with SHA-256, stored outside the web root under a randomized filename, and audited (`attachment.uploaded`). Disallowed extensions or mismatched MIME/magic bytes are rejected with HTTP `415 Unsupported Media Type` (`upload_type_not_allowed` / `upload_invalid_pdf`).
- **Screenshot / Evidence Required:**
  - `demo-13a-horizontal-ticket-isolation-404.png`: Student 1 visiting `/tickets/3` and receiving `Ticket unavailable`.
  - `demo-13b-vertical-role-restriction.png`: Student 1 visiting `/admin` and receiving `Access restricted`.
  - `demo-13c-internal-note-privacy-and-attachment.png`: Student 1 viewing `/tickets/4` (showing only the public reply, zero internal notes, and the uploaded attachment).
