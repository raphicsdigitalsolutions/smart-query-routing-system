# Project Overview

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
Google, SMTP, Meta WhatsApp, and OpenAI verification remain operator actions. See
`docs/RELEASE_READINESS.md` for the final deployment decision.

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

### Explicitly pending or blocked

- Instructor-level automatic assignment and automatic status polling/SSE.
- Password-login/registration audit events.
- Live provider verification and public deployment approval.
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
