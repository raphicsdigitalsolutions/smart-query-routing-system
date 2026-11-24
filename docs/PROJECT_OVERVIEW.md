# Project Overview

> **Current verified release status (2026-11-24):** Technical release artifacts are published and verified; formal institutional/governance approval and live provider verification remain open. Authoritative evidence: `docs/evidence/phase5_live_verification_2026-11-24.json`. Current verdict: **TECHNICAL RELEASE COMPLETE; FORMAL APPROVAL PENDING**.

## Problem statement

Universities receive a high volume of student queries through scattered channels: email, portals,
social messaging and in-person requests. These queries are often misrouted, answered late or
duplicated across departments. Students lack visibility into the status of their requests, staff
spend time on manual triage, and administrators have little insight into response times or SLA
compliance.

## Proposed solution

The **University Intelligent Communication Hub** provides a single authenticated entry point for
queries. Phase 4 captures each request as a ticket, scopes visibility by role, records a full status
and assignment history, and keeps an audit trail of privileged actions. Phase 5 adds a separate
Next.js App Router frontend that uses the same API and role rules, with the JWT kept in an HttpOnly
cookie behind a small same-origin BFF. Phases 6–7 add governed AI classification/routing/drafting,
per-user OpenAI BYOK, approved knowledge, SMTP/WhatsApp notifications, SLA escalation, analytics,
reporting, announcements, leave, audit, and Docker packaging. Humans remain in control of final
decisions.

The current implementation covers Phases 1–7. Provider-dependent behavior is tested offline; live
Google, SMTP, Meta WhatsApp, and real-user BYOK verification remain operator actions. Technical
release artifacts are published and verified; formal institutional/governance approval remains
pending. Authoritative state: `docs/evidence/phase5_live_verification_2026-11-24.json`. Current
verdict: **TECHNICAL RELEASE COMPLETE; FORMAL APPROVAL PENDING**.

## Main users and roles

| Role | Responsibilities |
| --- | --- |
| Student | Register, submit queries, view their own tickets, read public staff replies. |
| Staff | Work tickets assigned to them, reply publicly or with internal notes, update allowed statuses. |
| HOD | View department tickets, assign work, escalate, and update priority/status. |
| Administrator | View all tickets, manage departments, assign any eligible user and override workflow fields. |
| System services | Governed AI agents, encrypted BYOK resolution, email/WhatsApp delivery, notification and SLA workers. |

Public registration always creates a `student` account. Staff, HOD and admin accounts are created
only through an authorized administrative process; the current dev-only first-admin CLI is the sole
provisioning path.

## Core features

### Available now (Phases 1–7)

- FastAPI service with root, liveness, versioned status and database readiness endpoints.
- Centralized settings, CORS, predictable JSON error payloads and `.env.example` files.
- PostgreSQL persistence with SQLAlchemy 2.x and Alembic migrations.
- Argon2id password hashing, PyJWT access tokens and environment-only JWT signing keys.
- `student`, `staff`, `hod` and `admin` roles enforced by backend dependencies.
- Ticket creation, role-scoped listing/filtering, detail, updates, assignment, messages and history.
- Controlled six-state lifecycle with status/assignment history and audit logging.
- Unique public ticket references, transactional writes and hidden existence for unauthorized IDs.
- Internal staff notes hidden from students.
- Vite reference app with real login/registration, protected routes, role-aware navigation and live
  ticket screens.
- Next.js App Router frontend with TypeScript strict mode, MUI + shadcn-style Radix primitives,
  Tailwind v4, Lucide icons, centralized typed API client, loading/error states and responsive shell.
- Same-origin BFF with HttpOnly JWT cookies, CSRF double submit and no browser-side token storage.
- Migrated student, staff, HOD and admin views, including ticket submission, replies, internal notes,
  assignment, escalation, status changes, history and department administration.
- Dev-only first-admin provisioning CLI with production and duplicate-admin guards.

### Added in Phases 6–7

- Bounded LangGraph/LangChain AI classification, department routing, grounded drafting, validation,
  approval gate, per-user rate limiting, and sanitized errors.
- Per-user OpenAI BYOK with Fernet encryption at rest, user-scoped resolution, no global production
  fallback, status metadata only, and a documented safe rotation CLI.
- Approved knowledge documents with upload validation, versioning, approval/deactivation, and
  approved-source-only retrieval.
- SMTP and Meta WhatsApp adapters with deduplication, retry/attempt tracking, delivery rows,
  internal-note and unapproved-draft suppression, and a protected inbound intake path.
- Deterministic 24-hour SLA escalation, role-scoped analytics, PDF/XLSX reports, announcements,
  leave/auto-reply, audit API, Google OAuth, and ticket attachments.
- Production Dockerfiles and Compose stack with non-root images, health checks, migrations,
  persistent PostgreSQL and attachments, backup/restore and rollback guidance.

### Added in the 2026-11-23 reconciliation (local verification)

- Deterministic, staff-only instructor routing (FR-04b/FR-13): active `InstructorLeave` windows are
  excluded, HOD/admin accounts are never auto-assigned, and overrides remain audited
  (`backend/tests/test_instructor_routing.py`). No in-app leave-approval workflow exists.
- Conditional status polling (FR-06): `GET /api/v1/tickets/{id}/updates` returns an ETag/`304 Not
  Modified` snapshot consumed by the `useTicketStatusPolling` hook. This is **polling, not
  SSE/WebSocket push**.
- Secret-protected escalation trigger (FR-07): `POST /api/v1/tickets/escalation/sweep` with
  `X-Cron-Secret` and a daily `0 0 * * *` `backend/vercel.json` schedule
  (`backend/tests/test_escalation_serverless.py`). The live cron list confirms the schedule;
  **actual hosted invocation is NOT VERIFIED**.
- Password register/login success and failure audit events without passwords or secrets (FR-14,
  `backend/tests/test_auth_audit.py`).
- `backend/tests/test_token_expiry.py` asserts the production 60-minute default; the 1440-minute
  lifetime is test-only.
- Playwright + axe E2E suite: `npm run test:e2e` → `12 passed (2.0m)` with a successful webpack
  build (`12/12` pages) and no serious/critical axe violations on login, student workspace or ticket
  detail. Vitest `3 passed`; lint/typecheck PASS.
- Final full backend suite: `229 passed, 17 warnings in 410.30s (0:06:50)`, 0 failed/errors; focused
  malware/attachment tests: `10 passed, 17 warnings in 7.63s`.
- Backup/restore rehearsal PASS (`docs/evidence/backup_restore_rehearsal.json`) on a disposable
  `postgres:16-alpine` instance at `127.0.0.1:55432`, with matching schema/record hashes and stale
  rows 1 → 0; the container was removed and production was untouched.
- Optional malware scanning with a real ClamAV image verified `PASS_LOCAL_INTEGRATION_ONLY`
  (`docs/evidence/malware_scan_verification.json`); clean `OK`/exit 0 and in-container base64 EICAR
  `FOUND`/exit 1. A Windows-mounted EICAR fixture failed and is not claimed as a pass. Scanning is
  disabled by default (`MALWARE_SCAN_ENABLED=false`) and not deployed.

### Explicitly pending or blocked

- True SSE/WebSocket push is not implemented; FR-06 is conditional polling only.
- Live hosted escalation cron invocation and hosted `ESCALATION_CRON_SECRET` are **NOT VERIFIED**
  (schedule existence is verified via the live cron list).
- Live provider verification and formal institutional approval remain outstanding; current verdict
  is **TECHNICAL RELEASE COMPLETE; FORMAL APPROVAL PENDING** (`docs/evidence/phase5_live_verification_2026-11-24.json`). Netlify source sync is NOT VERIFIED.
- Secret audit (`docs/evidence/secret_audit.json`) recorded 17 workspace, 12 git-history and 453
  docker-image potential secrets plus 4 current-local-env matches; no rotation or revocation was
  performed.
- The 6 historical `npm audit` findings were remediated; both audits report **0 vulnerabilities**.
  GHCR publication is blocked by missing `write:packages`; the Docker Hub image is published and
  anonymously pull-verified.
- `release-v1` database was verified read-only: `neondb`, URL fingerprint `5d1fc726d19b`, host
  fingerprint `141f6064ec7f`, Alembic `feedf21773e1`, 17 public tables, 4 departments, 0 users,
  0 tickets, no writes; hosted equality not verified. Original production database previously checked
  read-only and not modified; not re-checked here.
- Original zero-cost Gemini/Claude/n8n/Baileys/Sheets toolchain conflicts with the approved OpenAI
  BYOK architecture and are not claimed.

## Design principles

- Keep configuration out of business logic.
- Keep HTTP handlers thin; place rules in service modules.
- Define explicit request/response schemas with Pydantic.
- Fail with predictable error structures.
- Preserve existing data; make every schema change through Alembic.
- Never store plaintext passwords, hardcode JWT secrets or expose privileged roles through public
  registration.
- Build incrementally and preserve data: migrations are additive and destructive database operations
  are prohibited.
