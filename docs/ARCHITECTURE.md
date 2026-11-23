# Architecture

> **Deployment addendum (2026-11-22):** A live hackathon deployment now exists: Next.js BFF on Netlify, FastAPI on Vercel Hobby, and Neon PostgreSQL. The diagrams below remain the application architecture reference; the live topology, serverless deviations, and verified endpoints are in `docs/HACKATHON_DEPLOYMENT_REPORT.md`.
>
> **Reconciliation addendum (2026-11-23):** Instructor routing is implemented in `app/services/instructor_routing.py` and is deterministic and staff-only (active `InstructorLeave` windows excluded, HOD/admin never auto-assigned, no in-app approval workflow). FR-06 is conditional polling (`GET /tickets/{ticket_id}/updates` with ETag/304 plus the frontend `useTicketStatusPolling` hook), not SSE/push. FR-07 adds a secret-protected `POST /tickets/escalation/sweep` and an hourly entry in `backend/vercel.json`; live hosted cron execution is **NOT VERIFIED**. Password registration/login success and failure audit events exist without passwords/secrets. Optional malware scanning is local-integrated only and disabled by default. University approval for scope deviations, tool/model/hosting substitutions, the zero-cost interpretation, the leave workflow and public-release governance is still outstanding; the prior `FAIL — DO NOT DEPLOY` verdict remains.

## High-level view

```text
Browser
├── Vite reference app (port 5173)
│   └── Axios + in-memory Bearer token (VITE_API_BASE_URL)
└── Next.js App Router app (port 3000) - the deployed UI/BFF
    └── same-origin /api/* route handlers
        ├── /api/auth/*            login, register, logout, me, session, google
        ├── /api/backend/[...path] authenticated BFF proxy to FastAPI /api/v1
        ├── /api/reports/[format]  streams backend PDF/XLSX through the BFF
        ├── /api/health            unversioned health proxy
        ├── HttpOnly smartquery_session cookie -> Bearer token to FastAPI
        ├── smartquery_csrf cookie + x-csrf-token header on unsafe methods
        └── typed client -> NEXT_PUBLIC_API_BASE_URL / API_BASE_URL (/api/v1)
                 |
                 v  (server-side only; port 8000 is never called by the browser)
FastAPI application (port 8000)
        ├── app/main.py          app wiring, CORS, middleware, error handlers,
        │                        lifespan + production-only SLA sweep worker
        │                        (disabled in the serverless deployment; cron trigger below)
        ├── app/api              versioned routers (/api/v1), auth dependencies
        │                        Phase 7: settings, knowledge, notifications,
        │                        analytics, announcements, leave, audit,
        │                        reports, integrations, operations, oauth
        ├── app/agents           bounded 5-node LangGraph, nodes, tools
        │   └── services         injectable OpenAI wrapper; analysis persistence,
        │                        approval boundary and BYOK key resolution
        ├── app/schemas          Pydantic request/response contracts
        ├── app/core             settings (production secret policy), enums,
        │                        security helpers, Fernet encryption, errors
        ├── app/db               declarative base, engine, sessions, dependencies
        ├── app/models           16 ORM tables (Phase 1-7), workflow history,
        │                        AI analyses and governed knowledge
        ├── app/services         ticket workflow, RBAC/ownership, audit and the
        │                        Phase 7 capability services (BYOK, knowledge,
        │                        notifications, email, WhatsApp, auto-routing,
        │                        instructor routing, malware scanning, escalation,
        │                        analytics, announcements, leave, reports, Google OAuth)
        └── app/cli              dev-only admin provisioning and operator-run
                                 OpenAI connectivity probe
                 |
                 v
PostgreSQL 16 (Docker container `postgres`, internal network only)
        <-- Alembic migrations on backend startup (revision head feedf21773e1)
```

Phase 1–5 established authentication, role rules, the ticket workflow and the
initial data model. Phase 6 added one additive AI table (`ticket_ai_analyses`),
four authenticated `/api/v1/ai` routes and a staff-only frontend panel without
changing existing routes or workflow. Phase 7 is additive: it adds nine tables,
six columns to `tickets`, eleven new route modules, the Phase 7 services above,
and new UI pages. It does not recreate or delete any earlier table or row. Both
frontends consume the same `/api/v1` contracts; the Next.js app renders the
Phase 6 and Phase 7 panels.

## Frontend architecture

### Vite reference app (`frontend/`, unchanged)

- `src/main.jsx` mounts the React app; `src/App.jsx` defines public and protected routes.
- `src/context/AuthContext.jsx` owns the user and keeps the JWT in module memory only.
- `src/services/api.js` is the single Axios client; a 401 clears the token and dispatches
  `auth:unauthorized`.
- Pages and components are organized under `src/pages/`, `src/components/layout`,
  `src/components/tickets` and `src/components/common`.
- Tailwind v4 runs through `@tailwindcss/vite`; navy/teal tokens live in `src/index.css`.

The Vite token disappears on reload and is not shared with the Next.js app.

### Next.js app (`frontend-next/`, Phase 5, extended in Phase 7)

```text
src/app/
├── layout.tsx                 root layout, MUI cache, providers, Toaster, metadata
├── globals.css                Tailwind v4 theme tokens and minimal global resets
├── page.tsx                   redirect to /dashboard
├── (auth)/login|register      public auth screens (+ Google Identity Services button)
├── (protected)/layout.tsx     server-side current-user check + AppShell
├── (protected)/dashboard      role-aware overview
├── (protected)/student        submission form, filters, ticket list
├── (protected)/staff          assigned queue
├── (protected)/hod            department overview
├── (protected)/admin          departments, assignable users, ticket overview
├── (protected)/tickets/[id]   conversation, AI panel, history and workflow controls
├── (protected)/analytics      SQL-backed overview charts
├── (protected)/knowledge      governed document list, upload and approval controls
├── (protected)/notifications  notification centre
├── (protected)/announcements  role/department-scoped broadcasts
├── (protected)/leave          leave windows and auto-reply text
├── (protected)/audit          admin-only audit log reader
├── (protected)/settings       personal BYOK key + integration status flags
├── api/auth/login|register|logout|me|session|google
├── api/backend/[...path]      authenticated BFF proxy to FastAPI /api/v1
├── api/reports/[format]       streams PDF/XLSX reports from the backend
├── api/health                 unversioned health proxy
├── loading.tsx, error.tsx, global-error.tsx, not-found.tsx
```

- `src/components/providers/AppProviders.tsx` composes the MUI theme provider, session provider and
  Sonner toaster. `layout.tsx` uses `@mui/material-nextjs/v16-appRouter` for SSR-safe Emotion styles (upgraded alongside Next.js `16.4.6` + Zod `4.6.7` + Vitest `4.1.12` on 2026-11-24).
- `src/components/layout/AppShell.tsx`, `Sidebar.tsx` and `Topbar.tsx` provide a responsive shell;
  navigation items and role badges come from the live client session.
- `src/components/auth/RoleGuard.tsx` hides unauthorized role views; `GoogleSignInButton.tsx` renders
  the official Google Identity Services button only when `NEXT_PUBLIC_GOOGLE_CLIENT_ID` is set. The
  FastAPI service layer still enforces the real permissions.
- `src/components/tickets/` contains the create form, filters, MUI table, conversation, internal-note
  controls, assignment dialog, workflow panel, staff-only `AiAssistPanel`, history timeline, and
  `TicketAttachments.tsx` for validated PDF/TXT/MD uploads.
- `src/components/admin/DepartmentManager.tsx` uses MUI dialogs/tables for admin department upkeep.
- `src/components/common/` holds status pills, loading/error/empty states, stat cards, backend status
  and pagination.
- `src/components/ui/` holds shadcn-style wrappers over Radix (`button`, `card`, `input`, `textarea`,
  `label`, `select`, `dialog`, `dropdown-menu`, `popover`).
- `src/hooks/useSession.ts`, `useTickets.ts` and `useBackendStatus.ts` centralize client data state;
  all ticket fetches accept `AbortSignal` for cancellation. `useTicketStatusPolling.ts` polls the
  lightweight ETag/304 status-snapshot endpoint (about every 15 s) and notifies the UI only on real
  changes; it is polling, not SSE/push. E2E coverage is in `frontend-next/e2e/` (Playwright + axe).
- `src/lib/api/types.ts` is the TypeScript mirror of the FastAPI response contracts and role/status
  maps. `client.ts`, `endpoints.ts` and `errors.ts` are the only browser-side API layer; Phase 7
  adds `apiKeysApi`, `knowledgeApi`, `notificationsApi`, `analyticsApi`, `announcementsApi`,
  `leaveApi`, `auditApi`, `escalationApi`, `integrationsApi`, `ticketsApi.uploadAttachment()`,
  `ticketsApi.listAttachments()` and `downloadReport()`.
- `src/lib/api/server.ts` is the server-side FastAPI caller used by BFF route handlers, including
  `serverApiRaw()` for streamed report responses.
- `src/lib/auth/cookies.ts`, `csrf.ts` and `session.ts` implement the HttpOnly session, CSRF and
  server-side current-user lookup. Google credentials are exchanged at `/api/auth/google`, which
  calls FastAPI `/auth/google` and then sets the normal HttpOnly session; the credential is never
  written to browser storage.

### MUI vs shadcn usage

| Use MUI | Use shadcn-style Radix wrappers |
| --- | --- |
| App theme and SSR emotion cache | Accessible dropdowns, selects, popovers |
| `TextField`/`Select` in intake and filters | Buttons, cards, labels and text inputs |
| `Dialog`, `Table`, `MenuItem` in admin and assignment flows | Sonner toasts and small layout primitives |

Tailwind owns spacing/layout/colors; MUI components are themed to the same navy/teal palette. There is
no competing global reset: `globals.css` contains Tailwind tokens and minimal box-sizing/body rules.

## Phase 6 AI architecture (extended in Phase 7)

```text
Staff/HOD/admin ticket detail
  -> aiApi (same-origin BFF, CSRF + HttpOnly session)
  -> FastAPI /api/v1/ai/tickets/{id}/...
  -> require_staff_or_above + get_accessible_ticket()
  -> agents/services/agent_service.py
       -> BYOK resolve_api_key(db, user.id) (personal key; no production global fallback)
       -> sanitized minimal AgentState
       -> LangGraph run_workflow(...)
            classification -> routing -> knowledge_research -> response_drafting -> validation
       -> DatabaseKnowledgeRepository (approved + active knowledge_documents only)
       -> TicketAiAnalysis row + AgentRun telemetry row + audit rows
  -> explicit approve-draft (human) -> services/tickets.create_message() -> public message
  -> notification centre + email/WhatsApp delivery for the public message
```

### Graph workflow

1. **classification** — one OpenAI structured-output call produces `ClassificationOutput`
   (intent, category, urgency, language, entities, confidence, rationale). A fatal provider/output
   failure records a sanitized error and conditionally ends the graph.
2. **routing** — the model chooses only from active departments and eligible staff supplied by
   `list_departments()` / `list_assignable_users()`. Unknown IDs are rejected; the ticket's existing
   validated department is the fallback. No assignment is performed by the graph.
3. **knowledge_research** — `DatabaseKnowledgeRepository` performs deterministic keyword retrieval
   over approved, active `knowledge_documents`, optionally scoped to global documents plus the
   caller's department. The earlier in-memory repository and optional `AI_KNOWLEDGE_FILE` remain for
   tests/local use. An empty repository yields `no_evidence=True` and forces abstention. Retrieved
   passages carry stable citations of the form `kb-{document_id}-v{version}`.
4. **response_drafting** — one structured call produces `DraftOutput`. Source references outside
   the retrieved approved set are removed. With evidence, approved `[source_id]` citations are
   inserted into the body if the model omitted them; with no evidence, all citations are removed and
   an uncertainty fallback body is used on provider failure.
5. **validation** — deterministic, no model call. It checks classification/routing availability,
   confidence thresholds, body length, source subset, inline citations, evidence requirement and
   explicit uncertainty when no evidence exists.

The graph has a fixed five-node shape and `AI_GRAPH_RECURSION_LIMIT=12`; retries live in the LLM
wrapper (`AI_LLM_ATTEMPTS`), not in graph cycles. A monotonic deadline and per-request SDK timeouts
bound every call. SDK-internal retries are disabled so the explicit budget cannot be exceeded.

### Trust boundaries

- A personal (BYOK) key, when present, takes precedence over `settings.OPENAI_API_KEY` in the LLM
  wrapper. It is passed only to the official SDK client; it is never sent to the browser, embedded
  in a prompt, logged or returned by an endpoint.
- Ticket text is redacted (`app/agents/tools/privacy.py`) before prompting; email addresses, obvious
  phone/long numbers, credential assignments and provider-token patterns become placeholders. The
  student name, email, password hash, internal notes and other domain records are never added to
  agent state. Ticket text remains untrusted data inside prompts.
- Agents have no SQL/session write capability. Routing uses existing service functions; analysis
  persistence and approval use `AgentService`; public messages use the existing `create_message()`.
- `approve-draft` is the only publish path. It is an explicit authenticated staff/HOD/admin action,
  rejects closed tickets through the existing message service, refuses drafts whose validation
  failed, and is idempotent per current analysis. It records both `ai.draft_approved` and the
  service's `message.created` audit rows.
- Errors are collapsed to stable categories such as `timeout`, `rate_limited` or `invalid_response`.
  Provider exception bodies, prompts and raw responses are never persisted or surfaced.
- Every real run writes an `agent_runs` telemetry row (model, token counts, duration, status). A
  per-user count of recent rows enforces `AI_RATE_LIMIT_PER_MINUTE` (default 20).

### Persistence and configuration

`TicketAiAnalysis` stores one version per run, the current-version flag, structured JSON outputs,
validation metadata, sanitized errors, execution metadata and approval columns. Its additive Alembic
revision is `b7d4e91c2a83`; Phase 7 adds `agent_runs` alongside it.

Relevant server settings in `backend/.env.example`: `OPENAI_API_KEY`, `OPENAI_MODEL`,
`OPENAI_TIMEOUT_SECONDS`, `AI_MAX_INPUT_TOKENS`, `AI_MAX_OUTPUT_TOKENS`, `AI_LLM_ATTEMPTS`,
`AI_GRAPH_TIMEOUT_SECONDS`, `AI_GRAPH_RECURSION_LIMIT`, `AI_MIN_CONFIDENCE`, `AI_KNOWLEDGE_FILE`,
plus Phase 7 controls `AI_RATE_LIMIT_PER_MINUTE`, `BYOK_ENCRYPTION_KEY` and
`ALLOW_GLOBAL_OPENAI_FALLBACK`. The optional legacy knowledge JSON file is external to the database.

## Phase 7 platform capabilities

### BYOK encrypted personal OpenAI keys

- `app/services/byok.py` is the only credential lifecycle service. Every read, save, validation and
  delete is scoped to the authenticated `user.id` and `provider='openai'`.
- Saving validates the candidate with a short `models.list()` probe (`max_retries=0`, 5s timeout),
  discards any provider exception text, then stores only a Fernet ciphertext plus a non-reversible
  `key_hint` (`****` + last four characters) in `user_api_keys`.
- `app/core/encryption.py` builds Fernet exclusively from `BYOK_ENCRYPTION_KEY` and fails closed
  with a generic 503 if the key is missing or malformed. Plaintext, ciphertext and hints are never
  logged.
- `resolve_api_key()` is the sole intentional plaintext egress, used by the agent service to build
  a per-run client; it updates `last_used_at` and is never logged.
- The `/settings/api-keys` endpoints return metadata only (`configured`, `is_valid`, `status`,
  `key_hint`, timestamps) — no full or partial secret beyond the display hint.
- The global `OPENAI_API_KEY` is only a gated development fallback; `_resolve_agent_api_key()` uses
  it only when `ALLOW_GLOBAL_OPENAI_FALLBACK` is true **and** `ENVIRONMENT != production`. Otherwise
  a missing personal key yields a stable `ai_personal_key_required` (402) response pointing the user
  to Settings. Settings validation additionally refuses to start in production with
  `ALLOW_GLOBAL_OPENAI_FALLBACK=true` or without `BYOK_ENCRYPTION_KEY`.

### Governed knowledge lifecycle

- `app/services/knowledge.py` owns upload/ingest, versioning, approval, deactivation, listing and
  retrieval wiring. Management is HOD/admin only; staff can read within scope.
- Ingest accepts inline text or `txt`/`md`/`pdf` uploads (`MAX_UPLOAD_BYTES`, `ALLOWED_UPLOAD_TYPES`).
  PDF text is extracted with `pypdf`; the file suffix determines parsing, never a declared mime type.
  Only extracted text, a logical file name and a SHA-256 checksum are stored — upload bytes are not
  retained in the database.
- Every upload creates a new row with a monotonic `version` per `source_key`
  (`uq_knowledge_documents_source_version`); `is_approved=False`, `is_active=True`. Approval,
  unapproval, activation, deactivation and metadata changes are audited via `record_audit`.
  Deactivation is a soft delete: the row stays auditable but is never retrieved.
- `DatabaseKnowledgeRepository` loads **only** `is_approved=True AND is_active=True` rows, with a
  global/department scope for non-admins, and returns `kb-{id}-v{version}` citation IDs. The research
  node cannot see unapproved or deactivated content, and the drafting/validation nodes strip any
  citation outside that retrieved set.

### Notification delivery

- `app/services/notifications.py` composes one plain-text body per event and records a
  `notifications` row per recipient/channel (`in_app`, `email`, `whatsapp`).
- In-app rows back the authenticated notification centre (`GET /notifications`,
  `POST /notifications/{id}/read` scoped by `recipient_user_id`). Email uses the standard-library
  SMTP transport with `SMTP_ATTEMPTS` retries and TLS/SSL options; WhatsApp uses the Meta Cloud API
  over `httpx`. Both outward transports return structured `DeliveryResult` values instead of raising,
  so a provider failure never breaks a ticket operation.
- Each row records `status` (`pending`/`sent`/`failed`), `attempts`, `last_error`, `provider_id` and
  `sent_at`. Outward delivery uses a 10-minute per-(ticket, event, recipient, channel) idempotency
  guard; recipients are de-duplicated and inactive users skipped.
- Only public state changes produce notifications (create, assign, public reply, leave auto-reply,
  SLA escalation, resolve, close). Internal notes do not produce notification rows, and unapproved
  AI drafts are never rendered into a body. Delivery requires `EMAIL_NOTIFICATIONS_ENABLED`/a real
  SMTP host and `WHATSAPP_ENABLED` with token + phone-number ID respectively; missing configuration
  simply produces no outward rows.

### Deterministic auto-routing and SLA escalation

- `app/services/auto_routing.py` tokenizes subject + description + category (stop-word filtering
  and simple singularization) and scores active departments by name/description keyword overlap.
  It is deterministic and LLM-free. No confident match (>= 2 score) raises `routing_unresolved`;
  ties break on the lowest department id. `TicketCreate.auto_route` or a missing `department_id`
  triggers routing, and the result is recorded in `audit_logs` as `ticket.auto_routed`.
- `app/services/instructor_routing.py` then selects an ordinary active `staff` instructor in the
  resolved department. Staff in an active `InstructorLeave` window are excluded (the end bound is
  exclusive), as are inactive users. Remaining candidates are ranked by their count of assigned
  tickets in non-terminal statuses, then lowercase `full_name`, then user ID. HOD and admin users
  are deliberately not auto-assigned. A successful selection writes assignment/status history, a
  `ticket.instructor_auto_assigned` audit row and one `TICKET_ASSIGNED` notification; no eligible
  instructor produces `ticket.instructor_routing_skipped` while the ticket remains department-routed,
  unassigned and in `new`. There is no approval workflow around this deterministic selection. Manual assignment via `POST /tickets/{id}/assign` is unchanged; the same active-window rule is shared with `active_auto_reply()` so on-leave staff are never auto-assigned. Verified locally by `backend/tests/test_instructor_routing.py` (exclusive end boundary, workload ranking, tie-breaks, audit/notification counts and no-eligible fallback).
- `app/services/escalation.py` marks every non-terminal ticket older than `SLA_HOURS` (default 24)
  as `is_escalated`, stamps `escalated_at`, writes a status-history row and an
  `ticket.escalated_automatically` audit row, and notifies the student, assignee, department HODs
  and admins. The `is_escalated=False` predicate makes the sweep repeat-safe.
- The sweep runs from a production-only async task in `app/main.py` every
  `ESCALATION_SWEEP_MINUTES` (default 60), can be triggered on demand by an admin via
  `POST /api/v1/tickets/escalation/run`, and has a secret-protected serverless trigger
  `POST /api/v1/tickets/escalation/sweep` (`X-Cron-Secret`, compared in constant time).
  `backend/vercel.json` schedules that path hourly (`0 * * * *`). LOCAL VERIFIED:
  `tests/test_escalation_serverless.py` and `tests/test_escalation.py`. The in-process worker is
  disabled on Vercel, and **live hosted cron execution is NOT VERIFIED**.

### Analytics, announcements, leave and auto-reply

- `app/services/analytics.py` computes every figure with SQL aggregates over the rows the caller
  may see (admin: all; HOD: department; staff: assigned; others: none). `GET /analytics/overview`
  (staff+) returns status/priority/channel counts, escalated/resolved/backlog totals, average first
  response time, department breakdown, latest-AI-category breakdown and a six-month volume series.
  No sample or placeholder data is used.
- `app/services/announcements.py` supports admin-created, role- and department-scoped broadcasts
  stored in `announcements`. Listing filters to active rows targeted at the caller's role and
  department; updates and deletion are soft/audited.
- `app/services/leave.py` manages `instructor_leaves` windows (staff own, HOD department, admin all)
  with an `auto_reply` text. `active_auto_reply()` is the exclusive lookup used by manual ticket
  assignment: when an assignee is on leave, a public auto-reply message is created and the student is
  notified. The same active-window semantics exclude on-leave staff from automatic instructor
  routing, so auto-assignment does not trigger an absence reply. Delete is a soft deactivation so
  the audit trail remains.

### Optional attachment malware scanning (local integration only)

- `app/services/malware_scan.py` is a fail-closed hook in the attachment upload path. It is disabled
  by default (`MALWARE_SCAN_ENABLED=false`) and does nothing without a configured
  `MALWARE_SCAN_COMMAND`. When enabled, exit 1 means `422 attachment_malware_detected` and any
  scanner error/missing binary/timeout means `503 attachment_scan_unavailable`; in both cases no
  message row or file bytes are retained. Scanner output containing file contents is not logged.
- LOCAL VERIFIED with the pinned `clamav/clamav:stable` image (clean file exit 0 / `OK`, EICAR
  fixture exit 1 / `FOUND`) and 10 focused tests; see `docs/evidence/malware_scan_verification.json`.
  A Windows mount fixture failed and is **not** claimed as passing. NOT DEPLOYED: no scanner service,
  command or hosted environment setting was changed.

### Audit and read APIs; PDF/Excel reports

- `audit_logs` is the shared append-only trail; `record_audit()` is used by ticket, knowledge, leave,
  announcement, AI, integration and password-auth flows. `GET /audit` (admin only,
  `app/services/audit.py`) is a filtered/paginated reader over real rows. `auth.registered`,
  `auth.login_succeeded` and `auth.login_failed` are recorded with email/reason context only — no
  password, token or API key. There are no synthetic audit rows.
- `app/services/reports.py` builds deterministic PDF (ReportLab, `invariant=1`) and XLSX (openpyxl)
  exports from role-scoped ticket rows with the same filter surface as the ticket list. Binary
  responses are streamed by `GET /api/v1/reports/tickets.pdf` and `/tickets.xlsx` (staff+) and pass
  through `GET /api/reports/[format]` in the BFF with `Cache-Control: no-store`.

### Token-gated inbound adapters and Google OAuth via BFF

- `app/api/routes/integrations.py` exposes `POST /integrations/email/inbound` and
  `POST /integrations/whatsapp/inbound`. Both require `X-Intake-Token` to match
  `INTAKE_WEBHOOK_TOKEN` via `hmac.compare_digest`; an unconfigured token rejects every request
  (fail-closed). Student identity comes from the explicit `student_email` mapping field — the
  untrusted `from_email`/`from_phone` headers are context only and never identify or create a user.
  Both call the existing `create_ticket()` with `channel='email'|'whatsapp'` and `auto_route` from
  the payload. `GET /integrations/status` returns only non-sensitive boolean flags.
- Google sign-in is a credential exchange through the BFF: the browser loads the official GIS
  script, posts the ID token to `POST /api/auth/google`, the BFF forwards it to
  `POST /api/v1/auth/google`, and `app/services/oauth_google.py` verifies signature (RS256 against
  Google JWKS), audience, issuer, expiry and `email_verified` before finding/creating a student
  account and a `user_oauth_accounts` link. External tokens never grant staff/HOD/admin roles.
  The BFF then sets the ordinary HttpOnly session and CSRF cookie.

## Request flows

### 1. Ticket creation -> auto-route -> notifications

```text
POST /api/v1/tickets (student) or POST /api/v1/integrations/{email,whatsapp}/inbound (token)
  -> services/tickets.create_ticket(db, payload, student)
       -> auto_route requested or department_id missing?
            -> services/auto_routing.resolve_department(...)  [deterministic, no LLM]
                 -> none: 400 routing_unresolved
                 -> match: department + matched keywords
       -> insert tickets row (channel, auto_routed, unique public_reference with retry)
       -> TicketStatusHistory(new) + audit ticket.created (+ ticket.auto_routed)
       -> services/instructor_routing.resolve_instructor(...)  [deterministic, no LLM]
            -> eligible active staff in department, excluding active leave windows
            -> lowest non-terminal workload, then lowercase full_name, then id
            -> found: assignment + status history, ticket.instructor_auto_assigned,
                     TICKET_ASSIGNED notification to that instructor only
            -> none: ticket stays new/unassigned, ticket.instructor_routing_skipped audit
       -> select active staff/HOD/admin in the department (plus admins),
          excluding an auto-assigned instructor
       -> services/notifications.notify_ticket_event(TICKET_CREATED)
            -> in_app rows for every recipient
            -> email rows when SMTP configured
            -> WhatsApp rows when configured + phone override supplied
       -> commit; TicketResponse returned to caller
```

### 2. AI analysis -> BYOK -> approved-only knowledge -> bounded graph -> draft -> approval

```text
POST /api/v1/ai/tickets/{id}/analyze (staff+)  [CSRF + HttpOnly cookie via BFF]
  -> require_staff_or_above + get_accessible_ticket()  [404 if not owned/visible]
  -> rate limit from agent_runs in the last 60s
  -> resolve_api_key(user.id) -> personal key, else gated dev fallback, else 402
  -> LlmService(api_key=personal) with monotonic deadline
  -> sanitized AgentState (redacted subject/description, minimal metadata only)
  -> DatabaseKnowledgeRepository: approved + active knowledge_documents only
  -> LangGraph: classification -> routing -> knowledge_research
                 -> response_drafting -> validation
  -> persist ticket_ai_analyses version (is_current flipped) + agent_runs + audit
  -> draft stays private; no message and no notification is created
POST /api/v1/ai/tickets/{id}/approve-draft (explicit human action)
  -> reload current analysis (row lock on PostgreSQL), reject failed validation
  -> services/tickets.create_message(is_internal=False) -> public message
  -> audit ai.draft_approved + message.created
  -> notify public.reply to student/assignee
```

### 3. SLA escalation sweep

```text
production lifespan task (every ESCALATION_SWEEP_MINUTES) or admin POST /tickets/escalation/run
  -> services/escalation.run_escalation_sweep(db)
       -> candidates: is_escalated=False, status not in (resolved, closed), created_at <= now-SLA_HOURS
       -> for each: set is_escalated + escalated_at
                    -> TicketStatusHistory(from_status == to_status, "Automatically escalated ...")
                    -> audit ticket.escalated_automatically (system actor)
                    -> recipients: student, assignee, dept HODs, all admins
                    -> notify_ticket_event(TICKET_ESCALATED)
       -> one commit; returns {scanned, escalated}
```

### 4. Knowledge upload -> approval -> retrieval

```text
HOD/admin POST /api/v1/knowledge (multipart text/txt/md/pdf)
  -> services/knowledge.create_knowledge_document
       -> validate type/size/department scope, extract text, SHA-256 checksum
       -> insert knowledge_documents (version = max+1 for source_key,
          is_approved=False, is_active=True) + audit knowledge.document_uploaded
HOD/admin PATCH /api/v1/knowledge/{id} {is_approved:true} (is_active:false to deactivate)
  -> set approved_by_id / approved_at or is_active, audit the transition
Staff AI run
  -> agents/services/agent_service.get_database_knowledge_repository(db, user)
       -> DatabaseKnowledgeRepository loads only approved AND active rows
       -> deterministic keyword search -> kb-{id}-v{version} citations
       -> drafting keeps only those citations; validation rejects any others
```

### 5. Inbound email/WhatsApp -> token-gated ticket

```text
Trusted mail/webhook adapter -> POST /api/v1/integrations/email/inbound
                                POST /api/v1/integrations/whatsapp/inbound
  -> require X-Intake-Token == INTAKE_WEBHOOK_TOKEN (hmac.compare_digest, fail-closed)
  -> resolve student by explicit student_email (404 if unknown)
  -> services/tickets.create_ticket(channel='email'|'whatsapp', auto_route from payload)
  -> same auto-route + audit + notification chain as flow 1
```

### 6. Conditional status polling (FR-06)

The Next.js ticket detail page calls `useTicketStatusPolling()` about every 15 seconds with an
`AbortController` and an in-flight guard. The request flows through the same-origin BFF to
`GET /api/v1/tickets/{ticket_id}/updates`, which returns a small status snapshot with an ETag derived
from student-visible status fields. A matching `If-None-Match` yields HTTP 304 with no body and no
re-render; a change yields HTTP 200 with a new ETag and the UI updates via callback. This is
conditional polling only — no `EventSource`, WebSocket or push transport. Transient errors are
ignored and retried on the next interval. E2E coverage is `frontend-next/e2e/tickets.spec.ts`; live
hosted polling is not asserted.

## Data model

All tables use `app.db.base.Base` with the project naming convention and `TimestampMixin`
timestamps where applicable. Exact table names are from `backend/app/models`.

### Tables added by `feedf21773e1` (revision head; down_revision `b7d4e91c2a83`)

| Table (model) | Key columns | Relationships / constraints |
| --- | --- | --- |
| `user_api_keys` (`UserApiKey`) | `user_id`, `provider` (default `openai`), `encrypted_key`, `key_hint`, `is_valid`, `validated_at`, `last_used_at` | `user_id -> users.id` CASCADE; unique (`user_id`, `provider`); index on both. Plaintext key is never stored. |
| `user_oauth_accounts` (`UserOauthAccount`) | `user_id`, `provider` (default `google`), `provider_subject`, `provider_email`, `linked_at` | `user_id -> users.id` CASCADE; unique (`provider`, `provider_subject`); user index. |
| `knowledge_documents` (`KnowledgeDocument`) | `title`, `source_key`, `version`, `source_type`, `file_name`, `mime_type`, `checksum`, `content_text`, `department_id`, `uploaded_by_id`, `approved_by_id`, `approved_at`, `is_approved`, `is_active` | `department_id -> departments.id` SET NULL; `uploaded_by_id -> users.id` RESTRICT; `approved_by_id -> users.id` SET NULL; unique (`source_key`, `version`); check `source_type IN ('text','txt','md','pdf')`; approval and department indexes. |
| `notifications` (`Notification`) | `ticket_id`, `recipient_user_id`, `recipient_address`, `channel`, `event_type`, `subject`, `body`, `status`, `attempts`, `last_error`, `provider_id`, `sent_at`, `read_at`, `is_internal` | `ticket_id -> tickets.id` CASCADE; `recipient_user_id -> users.id` CASCADE; check `channel IN ('in_app','email','whatsapp')`; check `status IN ('pending','sent','failed')`; recipient/created and ticket/event indexes. |
| `announcements` (`Announcement`) | `title`, `body`, `audience_roles_json`, `department_id`, `created_by_id`, `published_at`, `is_active` | `department_id -> departments.id` SET NULL; `created_by_id -> users.id` RESTRICT; published index. |
| `instructor_leaves` (`InstructorLeave`) | `user_id`, `start_at`, `end_at`, `reason`, `auto_reply`, `is_active`, `created_by_id` | `user_id -> users.id` CASCADE; `created_by_id -> users.id` RESTRICT; check `end_at > start_at`; user/active index. |
| `message_attachments` (`MessageAttachment`) | `message_id`, `file_name`, `content_type`, `size_bytes`, `storage_path`, `checksum` | `message_id -> messages.id` CASCADE; message index. Metadata only; bytes stay outside the DB. |
| `agent_runs` (`AgentRun`) | `ticket_id`, `requested_by_id`, `analysis_id`, `workflow`, `model`, `status`, `prompt_tokens`, `completion_tokens`, `tool_io_json`, `permission_outcome`, `duration_ms` | `ticket_id -> tickets.id` CASCADE; `requested_by_id -> users.id` SET NULL; `analysis_id -> ticket_ai_analyses.id` SET NULL; check `status IN ('completed','failed','abstained')`; ticket/created index. |

### `tickets` extensions (same migration)

`channel` (`web`/`email`/`whatsapp`, default `web`, check + index), `auto_routed` (bool, default
false), `escalated_at`, `first_response_at`, `resolution_summary`. The `channel_valid` check and
`ix_tickets_channel_created` index are added alongside them.

### Earlier model relationships (unchanged)

`departments -> users/tickets`, `users -> tickets (student/assignee)`, `tickets -> messages`,
`tickets -> ticket_status_history`, `tickets -> ticket_assignment_history`,
`tickets -> ticket_ai_analyses` (with requested/approving user and approved message), optional
`users -> audit_logs`. `users.password_hash` is NOT NULL with an Argon2 placeholder for pre-auth
rows; `tickets` retains its priority/status constraints and indexes; public ticket references are
unique with collision retry.

### Migration chain

1. `44273a775ed8_initial_schema.py` — Phase 3 tables.
2. `47ebce833eae_auth_and_ticket_workflow.py` — Phase 4 auth columns, history/audit tables,
   constraints and indexes.
3. `b7d4e91c2a83_ticket_ai_analysis.py` — Phase 6 AI analysis table.
4. `feedf21773e1_phase7_platform_capabilities.py` — Phase 7 tables and `tickets` extensions.
   Additive: no existing table is recreated and no row is deleted.

Alembic reads its URL from application settings and imports all models into metadata. Application
code does not call `Base.metadata.create_all()` outside isolated tests.

## API communication

### Browser to Next.js

- The browser calls only same-origin `/api/backend/...`, `/api/auth/...`, `/api/reports/...` or
  `/api/health` paths.
- `NEXT_PUBLIC_API_BASE_URL` defaults to `http://localhost:8000/api/v1`; an optional server-only
  `API_BASE_URL` can override it. These are public URLs, not secrets.
- `apiFetch()` adds the CSRF header to every unsafe method, parses typed errors, notifies the session
  on 401 and passes `AbortSignal`s through hooks/components. Report downloads use a plain GET so
  they remain cookie-authenticated and CSRF-safe.
- No frontend file contains a hard-coded FastAPI URL; no browser code receives the JWT or a provider
  secret.

### Next.js BFF to FastAPI

- `src/app/api/backend/[...path]/route.ts` reconstructs `/api/v1/<path>`, reads the HttpOnly session
  cookie, attaches `Authorization: Bearer <token>`, forwards the method/body/query and returns the
  FastAPI status and JSON unchanged.
- The same handler requires `x-csrf-token` to equal the readable `smartquery_csrf` cookie for
  `POST`/`PATCH`/`DELETE`. Unsafe auth routes such as logout apply the same check.
- A 401 from FastAPI clears both cookies. Missing session returns a normalized 401.
- `/api/auth/login`, `/register` and `/google` call FastAPI, set the HttpOnly JWT cookie with the
  backend `expires_in`, generate a fresh CSRF cookie and return only the safe user payload plus CSRF
  token. `/api/auth/me` revalidates the session through `/auth/me`.
- `/api/reports/[format]` forwards binary responses with `Cache-Control: no-store`; `/api/health`
  proxies the unversioned backend health probe.

Because the browser never calls port 8000 directly, the FastAPI CORS allowlist only needs to cover
local Vite development origins.

## Authentication and authorization

- Passwords are Argon2id PHC strings; plaintext is never logged, echoed or persisted.
- Public registration ignores extra role/department fields and creates an active `student`.
- Login failures use one generic `invalid_credentials` response.
- JWTs contain `sub`, `role`, `type`, `iat` and `exp`, signed HS256 with `JWT_SECRET_KEY`. There are
  no refresh tokens; access tokens last 60 minutes by default.
- The Next.js session cookie is `HttpOnly`, `SameSite=Lax`, `Secure` in production and scoped to `/`.
  The CSRF cookie is readable so the client can echo it in `x-csrf-token`.
- Trade-off: cookie sessions survive page reloads and are less exposed to XSS than a JS-held token,
  but a deployed HTTPS site must set `Secure` (already tied to `NODE_ENV=production`) and should add a
  same-site/origin check at the edge. Double-submit CSRF protects unsafe methods; SameSite=Lax is a
  second layer, not a replacement.
- Role guards in the Next.js UI are advisory. FastAPI dependencies and ticket services recheck the
  live DB user and scope visibility: students see own tickets, staff see assigned tickets, HODs see
  department tickets, admins see all. Unauthorized IDs return 404; forbidden actions on visible IDs
  return 403. `analytics`, `reports`, `knowledge` and `leave` apply the same role/ownership scoping.
- Internal notes are filtered from students by the backend (`list_messages`). The Next UI also hides
  the internal-note checkbox from students, but the backend remains the authority; internal notes
  never generate notification rows.

## Security boundaries

| Boundary | Enforcement |
| --- | --- |
| Browser -> BFF | HttpOnly `smartquery_session` cookie, readable CSRF cookie echoed as `x-csrf-token` on unsafe methods, same-origin `/api/*` only, 401 clears cookies. |
| BFF -> FastAPI | Server-side `Authorization: Bearer` header from the cookie; upstream URL is not exposed to the browser; `serverApiRaw()` streams reports without leaking the backend host. |
| FastAPI roles/ownership | `get_current_user`, `require_student`, `require_staff_or_above`, `require_hod_or_admin`, `require_admin` recheck the DB user; services scope by student/assignee/department. |
| Hidden existence | `get_accessible_ticket()` raises `NotFoundError` (404) for IDs the caller cannot view; 403 is reserved for forbidden actions on visible IDs. |
| Internal notes | Students never receive them in message lists; no notification row is created for an internal note. |
| AI approval gate | Only `approve-draft` publishes, after validation passes, with idempotency per current analysis and an explicit audit trail. Drafts never notify. |
| Secrets at rest | Fernet (`BYOK_ENCRYPTION_KEY`) encrypts each user's personal key in `user_api_keys`; only a masked hint is returned. No browser/local storage of secrets. |
| Provider fallback | Production forbids `ALLOW_GLOBAL_OPENAI_FALLBACK` and requires `BYOK_ENCRYPTION_KEY`/`JWT_SECRET_KEY` at settings validation; the agent service repeats the non-production check before using the global key. |
| Intake adapters | `X-Intake-Token` compared with `hmac.compare_digest`; unconfigured token is fail-closed; student identity from mapped email, not untrusted headers. |
| Abuse controls | Per-user AI rate limit from `agent_runs`; bounded LLM attempts/deadline/token caps; 10-minute notification dedupe; SMTP retry cap; upload size/type limits; optional fail-closed malware scanning (disabled by default, local integration only). |
| Cron trigger | `POST /tickets/escalation/sweep` requires `X-Cron-Secret` matching `ESCALATION_CRON_SECRET` by constant-time comparison; unconfigured secret rejects all calls. Live hosted cron execution not verified. |
| Auth audit | Registration and password login outcomes are append-only audit rows with email/reason context only; no password, token or provider secret is stored. |
| Secret audit | `docs/evidence/secret_audit.json` and `docs/SECRET_AUDIT_REMEDIATION_PLAN.md` record redacted triage only (307 tracked, 16 workspace potential, 12 git-history potential, 453 docker-image potential, 4 current-local-env matches). No rotation or revocation was authorized or performed. |
| Supply chain/runtime | Both images run as non-root UID/GID 10001, contain no `.env`/secrets, use versioned base images (`python:3.11-slim`, `node:20-alpine`), and expose only health-checked services. |

## Backend architecture

- `main.py` creates the app, adds CORS, mounts `/api/v1`, registers error handlers, runs the
  production-only escalation task in the lifespan and disposes pooled DB connections on shutdown.
- `core/config.py` is the single source of settings, loaded from environment variables and
  `backend/.env` via Pydantic Settings. Its `model_validator` enforces the production secret policy.
- `core/enums.py` defines roles, lowercase persisted statuses/priorities and transition maps.
- `core/security.py` wraps Argon2id hashing and JWT creation/validation; production fails closed
  without a signing key. `core/encryption.py` wraps Fernet for BYOK secrets.
- `api/deps.py` provides `get_current_user`, `require_student`, `require_staff_or_above` and
  `require_hod_or_admin`; roles are validated from the token and rechecked against the DB.
- `api/router.py` aggregates all 17 routers under `/api/v1`, including the Phase 6 `ai_router` and
  the Phase 7 routers. Routes stay thin; business logic lives in `services/`.
- `agents/` contains the bounded LangGraph workflow, injectable OpenAI wrapper, read-only tools and
  the only AI write boundary (`agents/services/agent_service.py`).
- `schemas/` keeps OpenAPI documentation accurate and prevents password hashes or key material from
  entering responses.

## PostgreSQL integration

`docker-compose.db.yml` still defines exactly one service, `postgres:16`, for local development with
a health check, restart policy and the named volume `smartquery_postgres_data`. The production stack
is `docker-compose.yml` below.

- `app/db/base.py` owns the declarative base and naming convention; `TimestampMixin` supplies
  timestamps.
- `app/db/session.py` builds a SQLAlchemy 2.x engine with `pool_pre_ping=True` and exposes
  `SessionLocal` and `dispose_engine()`.
- `app/db/dependencies.py` provides `get_db()` and a safe `check_database_connection()` that maps
  driver failures to HTTP 503 without leaking DSNs or passwords.

## Deployment topology (`docker-compose.yml`)

```text
                      docker bridge: smartquerysystem_internal
  [public]  frontend:3000  ──BFF /api/v1──>  backend:8000 (expose only)
                                                   │
                                                   │ DATABASE_URL (postgres:5432)
                                                   v
                                        postgres:16 (expose only)
                                                   │
                                     external volume smartquerysystem_smartquery_postgres_data
```

- Project name `smartquerysystem`; one user-defined bridge network `smartquerysystem_internal`.
  Only `frontend` publishes a host port (`${FRONTEND_PORT:-3000}:3000`). `postgres` and `backend`
  use `expose` only; no host publication. A commented loopback-only backend debug port exists but is
  disabled by default. Outbound HTTPS for SMTP/OpenAI/Meta/Google is still allowed.
- `postgres`: `postgres:16`, `restart: unless-stopped`, `pg_isready` health check, data mounted at
  `/var/lib/postgresql/data` from the **external** volume named
  `smartquerysystem_smartquery_postgres_data`. Compose never creates, replaces or deletes it; never
  use `down -v` or `docker volume rm` with this project.
- `backend`: built from `backend/Dockerfile` (non-root `app` user), image `smartquery-backend:${IMAGE_TAG:-latest}`,
  `depends_on: postgres: service_healthy`, health check on `/health`. Its entrypoint runs
  `alembic upgrade head` unless `RUN_MIGRATIONS=false` (for scaled deployments that run migrations
  as a one-off). All Phase 7 settings and secrets are injected from the project `.env`/secret manager;
  no `.env` is copied into the image.
- `frontend`: built from `frontend-next/Dockerfile` (non-root `nextjs` user), image
  `smartquery-frontend:${IMAGE_TAG:-latest}`, `depends_on: backend: service_healthy`, health check
  on `/api/health`. Server-side `API_BASE_URL` defaults to `http://backend:8000/api/v1`;
  `NEXT_PUBLIC_*` values are compile-time build args, never secrets.
- Health checks gate startup ordering (`service_healthy`) for backend and frontend.
- This section describes the original local Compose packaging and intended topology; that packaging
  work performed no public deployment, image push, host contact, DNS change or provider registration.
  A later live hackathon deployment (Netlify/Vercel/Neon) is recorded in
  `docs/HACKATHON_DEPLOYMENT_REPORT.md`; it did not use this Compose topology.

## Explicit deviations and limits

- **Provider:** the original brief suggested Gemini/Claude free tiers; the approved derived proposal
  uses OpenAI (`gpt-4o-mini` by default). BYOK shifts inference cost to the end user but does not make
  the system free; zero-cost operation cannot be claimed.
- **WhatsApp:** the original Baileys (JS) bot is replaced by a provider-independent Meta Cloud API
  HTTP adapter for outbound delivery plus token-gated inbound webhook adapters. The GET
  `/integrations/whatsapp/webhook` handshake consumes `WHATSAPP_VERIFY_TOKEN`, while inbound ticket
  creation uses `INTAKE_WEBHOOK_TOKEN`; no live Meta verification is asserted here.
- **Automation/logging:** the original n8n + Gmail API + Google Sheets workflow is replaced by local
  FastAPI services — stdlib SMTP for email, SQL-backed `notifications`/`audit_logs`, and the
  production-only async escalation worker. No Sheets or n8n integration exists.
- **Deployment:** the original phase delivered only local Docker packaging and documentation; a later
  live hackathon deployment exists but is a demonstration, not an approved release. Live provider
  accounts, TLS termination, monitoring, backup and rollback remain operator responsibilities.
- **Governance:** university approval is still required for scope deviations, tool/model/hosting
  substitutions, the zero-cost interpretation, the leave workflow and release/public governance.
  The prior `FAIL — DO NOT DEPLOY` verdict remains; local verification does not clear it.
- **Registry:** GHCR publication remains BLOCKED by missing `write:packages`. All registry content,
  including `ghcr.io/raphicsdigitalsolutions/smart-query-system:latest`, was left untouched.
- **Known telemetry limit:** `agent_runs.permission_outcome` is currently always `allowed`; denial
  paths are rejected before a run row is written. Knowledge file bytes are not retained (extracted
  text and checksum only). Ticket attachment bytes, by contrast, are retained in
  `ATTACHMENT_STORAGE_DIR` with only metadata and a SHA-256 checksum in the database.
- **Testing evidence:** exact counts belong in `docs/TEST_REPORT.md` and the hackathon report. This
  document distinguishes LOCAL VERIFIED from LIVE/BLOCKED/NOT VERIFIED and claims no live provider
  verification. Run the suites and connectivity checks locally before release.

## Testing and validation strategy

- Backend tests (`backend/tests/`) use a fresh in-memory SQLite database per test and mocked model
  providers (`conftest.py`, `ai_helpers.py`). Phase 7 coverage modules are `test_byok.py`,
  `test_knowledge.py`, `test_notifications.py`, `test_escalation.py`, `test_analytics.py`,
  `test_announcements.py`, `test_leave.py`, `test_audit.py`, `test_reports.py`, `test_integrations.py`,
  `test_attachments.py` and `test_oauth.py`, plus `test_instructor_routing.py`, `test_escalation_serverless.py`, `test_auth_audit.py`, `test_token_expiry.py`, `test_malware_scan_service.py` and `test_attachment_malware.py`, alongside the Phase 4–6 modules.
- `app/cli/test_openai.py` is an operator-run connectivity probe that makes a real minimal request;
  it is not part of the automated suite. This document does not claim that probe (or any provider
  call) succeeded.
- Frontend scripts (`npm run typecheck`, `npm run lint`, `npm run build`) are the intended static
  checks; recorded results are in `docs/TEST_REPORT.md` and `docs/HACKATHON_DEPLOYMENT_REPORT.md`.
- Browser-level verification is now automated: Playwright specs cover login, ticket submission,
  polling, cross-user isolation and workflow, and `@axe-core/playwright` checks login, student
  workspace and ticket detail. LOCAL VERIFIED: build passed and 11 tests passed (~1.3 min), with no
  serious or critical axe violations on those three screens. This is local evidence only; no live
  hosted browser run is asserted. After installing Playwright/axe, `npm audit` reported 6
  vulnerabilities (2 moderate, 2 high, 2 critical), which remain an open remediation item.
- LOCAL VERIFIED backup/restore rehearsal (`docs/evidence/backup_restore_rehearsal.json`, status
  `PASS`): disposable `postgres:16-alpine` at `127.0.0.1:55432`, schema hash
  `ed7d1ab744886956c3e35ddde4674a05b01da26ef8313199b2c741e35917664b`, record hash
  `00e07e9f6182a27c59db5e2b9b0d51055011c13029485c4647b9ba4cc994d419`, stale row count 1 → 0,
  container removed; no production data touched. This is a local rehearsal, not a hosted Neon restore.
- Backend evidence at the time of this reconciliation: the full suite before the latest
  malware-service tests was 218 passed / 17 warnings in 235.04s, the focused malware/attachment run
  was 10 passed, and the final full backend rerun completed with 225 passed, 17 warnings in 265.61s
  (0:04:25). The 17 warnings are pre-existing LangSmith deprecations.
