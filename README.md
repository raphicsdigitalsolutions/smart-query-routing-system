# Smart Query Routing & Email Automation System

**Project:** University Intelligent Communication Hub

A production-oriented university query-routing system. This checkout contains the Phase 1–4
FastAPI/PostgreSQL/React foundation, **Phase 5: a separate Next.js App Router frontend**,
**Phase 6: bounded staff-only AI assistance**, and **Phase 7: platform capabilities and integration
packaging**. Phase 7 includes BYOK OpenAI keys, approved knowledge, notifications with SMTP and
WhatsApp adapters, Google OAuth2, auto-routing/escalation, analytics, announcements, leave,
reports, audit, and full-stack Docker Compose packaging. The original Vite app is kept untouched as
the working reference.

> **Deployment addendum (2026-11-24 final verification):** A live hackathon deployment was executed:
> Next.js BFF on Netlify, FastAPI on Vercel Hobby, and Neon PostgreSQL. The current status is
> **TECHNICAL RELEASE COMPLETE; FORMAL APPROVAL PENDING**: technical release artifacts are published
> and verified, while formal institutional/governance approval and live provider verification remain
> open. See `docs/HACKATHON_DEPLOYMENT_REPORT.md` for the original deployment record,
> `docs/RELEASE_READINESS.md` for the current release verdict, and
> `docs/HACKATHON_DEPLOYMENT_SLIDES.pdf` for the presentation. Live provider features still require
> real credentials and provider approval.

## Main objectives

- Give students a single place to submit academic and administrative queries.
- Route each query to the correct department or staff member, with auditable overrides.
- Keep staff, HODs and administrators informed through an auditable ticket workflow.
- Provide role-scoped views without weakening backend authorization.
- Keep a production-ready Next.js migration separate from the reference Vite app.
- Support optional provider-backed channels and BYOK AI only when configured by the deployment.

## Technology stack

| Layer | Technologies |
| --- | --- |
| Backend | Python 3.11+, FastAPI, Uvicorn, Pydantic v2 / Pydantic Settings, SQLAlchemy 2.x |
| Database | PostgreSQL 16 (local Docker container), psycopg 3, Alembic migrations |
| Auth | Argon2id password hashing (`argon2-cffi`), JWT access tokens (`PyJWT`), optional Google OAuth2 |
| AI / BYOK | OpenAI Python SDK structured outputs, LangGraph, LangChain Core, Fernet-encrypted per-user keys, approved-only knowledge retrieval |
| Integrations | SMTP email notifications, Meta WhatsApp Cloud API adapter, protected inbound intake webhooks |
| Operations | Health checks, Alembic startup migrations, Docker Compose packaging, backup/restore and rollback documentation |
| Reference frontend | React, Vite, JavaScript, Tailwind CSS v4, Axios, React Router, Lucide React |
| Next.js frontend | Next.js App Router, React, TypeScript (strict), MUI, shadcn-style Radix primitives, Tailwind CSS v4, Lucide, Sonner |
| Development | Windows, VS Code / OpenCode, local dev servers |

## Folder structure

```text
SmartQuerySystem/
├── docker-compose.db.yml       # PostgreSQL ONLY (no app containers)
├── docker-compose.yml          # Full stack: postgres + backend + frontend
├── .env.example                # Production-stack Compose example (DB placeholders included)
├── backend/
│   ├── app/
│   │   ├── agents/              # Phase 6 bounded graph, nodes, tools and services
│   │   │   ├── nodes/           # classify, route, research, draft, validate
│   │   │   ├── prompts/         # versioned system/user prompt templates
│   │   │   ├── services/        # LLM wrapper and analysis/approval service
│   │   │   └── tools/           # read-only knowledge, routing and privacy helpers
│   │   ├── api/                 # Versioned routers (mounted at /api/v1)
│   │   │   ├── deps.py          # Auth and role dependencies
│   │   │   └── routes/          # auth, tickets, ai, knowledge, notifications, integrations,
│   │   │                        # oauth, operations, analytics, announcements, leave, reports,
│   │   │                        # audit, settings, departments, users, status
│   │   ├── cli/                 # Dev-only admin provisioning and OpenAI probe
│   │   ├── core/                # Settings, enums, security, errors
│   │   ├── db/                  # Declarative base, engine, sessions, dependencies
│   │   ├── models/              # users, tickets, messages, history, audit, BYOK keys, OAuth,
│   │   │                        # knowledge, notifications, announcements, leave, reports, AI analyses
│   │   ├── schemas/             # Pydantic request/response contracts
│   │   ├── services/            # Ticket workflow, authorization, routing and audit logic
│   │   └── main.py              # FastAPI application entry point
│   ├── evaluations/             # Synthetic offline agent-evaluation harness
│   ├── alembic/                 # Migration environment and versioned revisions
│   ├── tests/                   # API, auth, ticket, model, health, AI and integration tests
│   ├── .env.example
│   ├── pytest.ini
│   └── requirements.txt
├── frontend/                    # Phase 4 reference Vite app (unchanged by Phase 5+)
│   └── src/
│       ├── components/
│       ├── context/
│       ├── hooks/
│       ├── pages/
│       └── services/api.js
├── frontend-next/               # Phase 5 production migration
│   ├── src/app/                 # App Router routes and BFF route handlers
│   │   ├── (auth)/              # /login, /register
│   │   ├── (protected)/         # /dashboard, /student, /staff, /hod, /admin, /tickets/[ticketId],
│   │   │                        # /knowledge, /notifications, /settings, /analytics,
│   │   │                        # /announcements, /leave, /audit
│   │   └── api/                 # /api/auth/*, /api/health, /api/backend/[...path]
│   ├── src/components/          # auth, layout, common, tickets (incl. AI panel), admin, UI, providers
│   ├── src/hooks/               # useSession, useTickets, useBackendStatus
│   ├── src/lib/                 # typed API client, BFF helpers, auth/cookies/CSRF, config
│   ├── src/context/             # session context
│   ├── src/theme/               # shared MUI theme
│   ├── .env.example
│   └── package.json
├── docs/
└── README.md
```

## Local setup

### Prerequisites

- Python 3.11+ and Node.js 20+ with npm.
- **Docker Desktop** running for the local PostgreSQL container.

### 1. Configure environment placeholders

```powershell
copy .env.example .env
copy backend\.env.example backend\.env
copy frontend\.env.example frontend\.env
copy frontend-next\.env.example frontend-next\.env.local
```

All `.env.example` files contain placeholders only (no real credentials); the root example is a
production-stack template. Never commit any `.env` file.
Never place `JWT_SECRET_KEY`, OpenAI keys, SMTP passwords, WhatsApp tokens, database URLs or BYOK
encryption keys in `frontend-next/.env.local`; those secrets belong to the backend/Compose
environment.

The root `.env.example` is the production full-stack Compose example. It also supplies the
`POSTGRES_*` values for the local DB-only helper. If you run the backend from the host against
`docker-compose.db.yml`, override `DATABASE_URL` in `backend/.env` so the host is `localhost`
instead of `postgres`. For the full stack, replace every `REPLACE_WITH_*` value before building.

Set a long random JWT signing key in the backend environment:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

AI uses BYOK in production: each user adds a personal OpenAI key in account settings. The backend
encrypts it with `BYOK_ENCRYPTION_KEY`, never returns it, and does not use a global admin fallback
when `ALLOW_GLOBAL_OPENAI_FALLBACK=false`. `OPENAI_MODEL`, `OPENAI_TIMEOUT_SECONDS`,
`AI_MAX_INPUT_TOKENS`, `AI_MAX_OUTPUT_TOKENS`, `AI_LLM_ATTEMPTS`, `AI_GRAPH_TIMEOUT_SECONDS`,
`AI_GRAPH_RECURSION_LIMIT`, `AI_MIN_CONFIDENCE`, `AI_RATE_LIMIT_PER_MINUTE` and
`AI_KNOWLEDGE_FILE` are bounded server-side settings.

### 2a. Start PostgreSQL only (DB-only Compose)

`docker-compose.db.yml` contains **only** the `postgres` service; it does not start backend or
frontend containers.

```powershell
docker compose -f docker-compose.db.yml up -d postgres
docker compose -f docker-compose.db.yml ps        # wait until "healthy"
```

Data is preserved in the logical volume `smartquery_postgres_data` (resolved on this host as
`smartquerysystem_smartquery_postgres_data`). To stop without deleting data:

```powershell
docker compose -f docker-compose.db.yml stop postgres
```

### 2b. Full-stack Compose (production packaging; not deployed here)

`docker-compose.yml` is the full stack: `postgres`, `backend` and `frontend` under Compose project
`smartquerysystem`. It reuses the external volume `smartquerysystem_smartquery_postgres_data`.
**Never use `down -v` or delete this volume.**

Validate first:

```powershell
docker compose -f docker-compose.yml config
```

After filling the root `.env` with real values and obtaining deployment approval, build and start:

```powershell
docker compose -f docker-compose.yml build
docker compose -f docker-compose.yml up -d
docker compose -f docker-compose.yml ps
```

These are operator commands recorded in `docs/DEPLOYMENT_GUIDE.md`. Both images were built locally,
and an equivalent stack was smoke-tested with disposable containers/volumes. Starting this exact
Compose project against the existing external database volume, public deployment, and provider
verification were not performed. Stop without deleting data with
`docker compose -f docker-compose.yml down` (never `-v`).

### 3. Backend (local host development against the DB-only container)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Run the isolated tests (they use in-memory SQLite, never the development database):

```powershell
cd backend
pytest
```

The final full backend suite result is **229 passed, 17 warnings in 410.30s (0:06:50)**. The warnings
are pre-existing LangSmith `asyncio.iscoroutinefunction` deprecations. The suite includes the
FR-04b/FR-13 instructor-routing tests, FR-06 conditional-polling tests, FR-07 serverless-escalation
tests, FR-09 manual escalation/de-escalation history & notification tests, FR-14 auth-audit tests,
token-expiry assertions, ticket-grounded demo AI consistency tests, and attachment/malware tests. The
focused security/auth/malware/cron run is `64 passed, 17 warnings in 27.06s`, and the focused
escalation/ticket/notification/audit run is `42 passed, 17 warnings in 70.95s`. The current migration head is
`feedf21773e1`, and the OpenAPI schema registers 41 paths after adding ticket attachments and the
WhatsApp verification handshake. Automated tests do not call paid provider APIs. Exact commands and
results are in `docs/TEST_REPORT.md`; the release decision and operator actions are in
`docs/RELEASE_READINESS.md`.

### 4. Provision the first local administrator

Public registration always creates a `student`. Staff, HOD and admin accounts are never created by
the registration endpoint. Create the first admin with the guarded CLI:

```powershell
cd backend
$env:ADMIN_PASSWORD = '<your-strong-password>'
python -m app.cli.provision_admin --email admin@university.edu
```

Leaving `ADMIN_PASSWORD` unset uses a hidden prompt. The CLI refuses to run with
`ENVIRONMENT=production`, refuses a second admin and never echoes or stores plaintext. There is no
public role-escalation path and no backend user-CRUD endpoint.

### 5. Frontends

Reference Vite app (kept as the working reference):

```powershell
cd frontend
npm install
copy .env.example .env        # VITE_API_BASE_URL=http://localhost:8000
npm run dev
```

Production Next.js app:

```powershell
cd frontend-next
npm install
copy .env.example .env.local  # NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
npm run dev
```

Production build and server:

```powershell
cd frontend-next
npm run build
npm run start
```

Checks for the Next.js app:

```powershell
npm run typecheck
npm run lint
npm run build
```

## Local URLs

| Service | URL |
| --- | --- |
| Next.js frontend (Phase 5+) | http://localhost:3000 |
| Vite reference frontend | http://localhost:5173 |
| Backend root | http://localhost:8000/ |
| Liveness health | http://localhost:8000/health |
| Versioned API status | http://localhost:8000/api/v1/status |
| Database readiness | http://localhost:8000/api/v1/status/database |
| Interactive API docs | http://localhost:8000/docs |

## Phase 5 implementation status (historical)

**Done**

- Separate `frontend-next/` app; `frontend/` and `backend/` were not rewritten.
- Next.js App Router with TypeScript strict mode, ESLint, centralized config and responsive layout.
- MUI for forms/dialogs/tables/navigation, shadcn-style Radix primitives for accessible controls,
  Tailwind v4 tokens for layout, Lucide icons and Sonner toasts. Style layers do not conflict.
- Public login/registration and protected `/dashboard`, `/student`, `/staff`, `/hod`, `/admin` and
  `/tickets/[ticketId]` routes, plus loading, error, global-error and not-found screens.
- Student submission/filtering, staff replies/internal notes/status changes, HOD department review,
  assignment/escalation/status controls and admin department maintenance/assignable-user listing.
- Typed API client with centralized endpoints, typed errors, cancellation, CSRF handling and a
  same-origin Next.js BFF. No scattered backend URLs and no browser-side JWT.
- JWT only in an HttpOnly `smartquery_session` cookie; CSRF double-submit cookie/header on unsafe
  methods. No `localStorage`/`sessionStorage` credentials.
- Real live verification: registration/login, role navigation, ticket creation, public replies,
  internal notes, internal-note privacy, assignment, status transitions, escalation, admin controls,
  protected-route redirects and console checks.
- Backend tests, Alembic checks, Vite build and Next.js typecheck/lint/build all pass.

**Not part of Phase 5 (later work)**

- Gmail/email, WhatsApp, Docker application images and deployment config were added in Phase 7 as
  code/config only; at that historical point live provider verification and deployment were pending.
  A later hackathon deployment was executed — see the 2026-11-24 sections below.
- Google OAuth and BYOK were added in Phase 7. Refresh tokens, password reset, email verification
  and user-creation CRUD are still future work.
- Automated test suites for the Next.js frontend were manual/live plus static checks during
  Phase 5; a working-tree Playwright + axe suite was added later (see the 2026-11-23 evidence
  addendum below).

## Phase 6 implementation status (historical)

**Done**

- Bounded LangGraph workflow: `classification -> routing -> knowledge_research -> response_drafting
  -> validation`, with a conditional stop after a fatal classification failure.
- Official OpenAI SDK structured outputs with Pydantic schemas, fixed retries, a monotonic
  end-to-end deadline, per-request timeouts and sanitized error categories. No key, prompt body,
  raw response or provider exception text is logged or returned.
- Read-only tools only: approved-knowledge retrieval, backend-scoped department/staff lookup and
  deterministic ticket-text redaction. Agents cannot issue SQL or mutate domain records.
- One additive migration, `b7d4e91c2a83`, creates `ticket_ai_analyses` for versioned analysis,
  validation metadata, sanitized errors and idempotent human-approval state.
- Four staff-only endpoints under `/api/v1/ai`; `require_staff_or_above` plus
  `get_accessible_ticket()` enforce role and per-ticket visibility on every operation.
- AI never assigns, changes status, sends email or publishes messages. Only the explicit
  `approve-draft` endpoint publishes a draft, through the existing `create_message()` service and
  with both `ai.draft_approved` and `message.created` audit rows.
- Trusted-evidence rule: with no approved knowledge match the draft abstains and cites nothing;
  with evidence, approved source IDs must appear as inline citations in the draft body.
- Next.js staff/HOD/admin ticket detail panel shows analyze, classification, priority and
  department/staff recommendations, sources, draft, regenerate, approve, loading/success/error
  states and confirmation that output is not public until approved.
- Deterministic mocked-LLM tests cover structured-output validation/retry, redaction, graph order,
  routing fallback, source filtering/citations, abstention, authorization, idempotent approval,
  one public message and audit rows.
- A historical OpenAI connectivity probe passed with model `gpt-4o-mini`; automated tests do not
  depend on it. Live HTTP smoke check confirmed all four routes, health and unauthenticated 401
  behavior.
- Phase 6 recorded backend `pytest -q` 62 passed, `compileall`, `alembic current/check`, Next.js
  typecheck/lint/build all pass.

**Not part of Phase 6 (later work)**

- Gmail/WhatsApp, Docker/application deployment, labelled routing-accuracy evaluation, refresh
  tokens, user CRUD and frontend automated tests. Phase 7 added the integrations, synthetic
  evaluation harness and packaging; live provider verification and public deployment were not done.

### Safe OpenAI probe

With `OPENAI_API_KEY` configured in `backend/.env`, run from `backend/`:

```powershell
.\.venv\Scripts\python.exe -m app.cli.test_openai
```

It performs one minimal real structured request and prints only status, model, attempts and
duration. Without a key it exits with `NOT CONFIGURED`; it never prints or accepts a key on argv.
This is a historical CLI probe, not a Phase 7 live-provider verification; production uses per-user
BYOK keys.

## Phase 7 implementation status

**Done**

- **Defect fixes and authorization:** fixed the staff AI authorization defect in real workflows,
  consolidated student/staff/HOD/admin visibility checks, kept invisible tickets at 404, protected
  internal-note privacy, and added per-user AI rate limiting (`ai_rate_limited` 429). The final
  targeted rate-limit regression test passed.
- **BYOK OpenAI:** users can add, validate, replace and delete their own OpenAI key. Keys are
  Fernet-encrypted with `BYOK_ENCRYPTION_KEY`, scoped to the user, status-only in the UI, never
  returned or logged. Production forbids a global fallback and fails closed when no personal key is
  configured.
- **Approved knowledge:** HOD/admin knowledge management supports upload, versioning, approval,
  deactivation and approved-source-only citations; unsupported answers abstain.
- **Notifications and SLA:** in-app history, SMTP email delivery, a Meta WhatsApp Cloud API adapter
  and protected inbound intake cover submission, assignment, public replies, escalation and
  resolution without exposing internal notes or unapproved drafts. `SLA_HOURS` and
  `ESCALATION_SWEEP_MINUTES` drive automatic overdue escalation and audit events.
- **Remaining original features:** optional Google OAuth2 sign-in through the BFF, deterministic
  auto-routing and instructor assignment with audited HOD/admin override, multi-channel intake,
  admin analytics, announcements, instructor leave/auto-reply, PDF/Excel reports and a
  system-wide audit log.
- **Docker Compose production packaging:** non-root backend and frontend Dockerfiles, a full-stack
  `docker-compose.yml`, health checks, internal networking, migration-safe startup, external
  PostgreSQL volume reuse and root env examples with no secrets baked into images.
- **Verification recorded:** migration head `feedf21773e1`; 41 OpenAPI paths; final full backend
  suite **229 passed, 17 warnings in 410.30s (0:06:50)**; frontend typecheck/lint/Vitest (`3 passed`)/
  build (`12/12` pages) passed; Playwright + axe E2E **12 passed in 2.0m**; both Docker images built
  and smoke-tested; Compose config validation passed for both files. See `docs/TEST_REPORT.md` and
  `docs/RELEASE_READINESS.md`.

**Limits and blocked checks**

- **Live hackathon deployment was executed after this historical packaging audit.** Formal production
  approval is still not granted. See `docs/HACKATHON_DEPLOYMENT_REPORT.md` for the actual Netlify,
  Vercel, and Neon endpoints and results.
- Live SMTP, WhatsApp, Google OAuth and OpenAI evaluation checks are **blocked pending real
  credentials/provider setup** and were not performed.
- The evaluation harness uses a synthetic 24-record dataset. Its results test pipeline wiring and
  guardrails; they are not real university accuracy or performance.
- BYOK shifts API cost to users; it does not satisfy the original zero-cost tooling constraint.

## Verification evidence addendum (2026-11-23)

This addendum reconciles stale test/QA claims with the local evidence available at that time. It
changes no credentials, registry, deployment, or production data. Its historical
`FAIL — DO NOT DEPLOY` governance verdict has since been superseded by the 2026-11-24 final
verification below; see `docs/RELEASE_READINESS.md` for the current disposition.

- **Full backend suite (final rerun):** from `backend/`, `.\.venv\Scripts\python.exe -m pytest -q` →
  `229 passed, 17 warnings in 410.30s (0:06:50)`. Earlier 187/202/218/225 counts in older notes are
  historical. The warnings are pre-existing LangSmith deprecations. Focused security/auth/malware/cron
  run: `64 passed, 17 warnings in 27.06s`; focused escalation/ticket/notification/audit run:
  `42 passed, 17 warnings in 70.95s`.
- **Browser E2E and accessibility:** `npm run test:e2e` in `frontend-next/` (its `pretest`
  `next build` passed) → `12 passed in 2.0m` in the final rerun (the earlier `1.5m` figure is
  historical). The working-tree Playwright + axe suite in
  `frontend-next/e2e/` covers login, student workspace, ticket detail, and manual
  escalation/de-escalation history & notifications; axe reported **no serious or critical violations**
  on those pages. Vitest polling-hook unit tests (`3 passed`), typecheck, lint, and build (`12/12`
  pages) passed. This is local verification, not a claim about the hosted deployment.
- **FR-04b / FR-13 instructor routing:** deterministic, staff-only assignment implemented in
  `app/services/instructor_routing.py`; active `InstructorLeave` windows are excluded, HOD/admin
  accounts are never auto-assigned, and overrides remain audited HOD/admin actions. Covered by
  `backend/tests/test_instructor_routing.py`. There is no in-app leave-approval workflow.
- **FR-06 status tracking:** conditional `GET /api/v1/tickets/{id}/updates` with ETag/`304 Not
  Modified` plus the frontend `useTicketStatusPolling` hook. This is **polling, not SSE/push**;
  covered by `tests/test_ticket_updates.py`, `useTicketStatusPolling.test.tsx` and an E2E case.
- **FR-07 escalation:** secret-protected `POST /api/v1/tickets/escalation/sweep` (`X-Cron-Secret`,
  constant-time check), covered by `backend/tests/test_escalation_serverless.py`. The schedule was
  corrected from the invalid hourly `0 * * * *` to the supported daily `0 0 * * *`
  (Vercel Hobby permits at most once/day); `backend/vercel.json` on current main matches the live
  deployment. **Schedule existence is verified; hosted cron invocation and escalation effect are
  NOT VERIFIED**, and no host or secret was changed.
- **FR-14 auth audit:** password register/login success and failure audit events are emitted without
  recording passwords or secrets (`backend/tests/test_auth_audit.py`).
- **Token lifetime:** `backend/tests/test_token_expiry.py` asserts the production default of 60
  minutes; the 1440-minute lifetime is test-only and must not be treated as a production setting.
- **Backup/restore rehearsal:** `docs/evidence/backup_restore_rehearsal.json` records `PASS` on a
  disposable `postgres:16-alpine` container at `127.0.0.1:55432`; schema hash
  `ed7d1ab744886956c3e35ddde4674a05b01da26ef8313199b2c741e35917664b` and record hash
  `00e07e9f6182a27c59db5e2b9b0d51055011c13029485c4647b9ba4cc994d419` matched after restore,
  stale row count went 1 → 0, and the container was removed. Production was not touched.
- **Malware scanning:** `docs/evidence/malware_scan_verification.json` records
  `PASS_LOCAL_INTEGRATION_ONLY`. Real ClamAV (`clamav/clamav:stable`, digest
  `sha256:64e30c0bf976198024deb3dc6d5cfe2485fb969c0f73549ba0fdb364b9469614`) returned `OK`/exit 0
  for a clean file and `Eicar-Test-Signature FOUND`/exit 1 for an in-container base64 EICAR fixture.
  A Windows-mounted EICAR fixture **failed** and is not claimed as a pass. Scanning is optional and
  `MALWARE_SCAN_ENABLED=false` by default; no scanner was deployed or configured.
- **Secret audit:** `docs/evidence/secret_audit.json` and
  `docs/SECRET_AUDIT_REMEDIATION_PLAN.md` report 385 tracked files, 17 workspace potential
  secrets, 12 git-history potential secrets, 453 docker-image potential secrets and 4 matches
  against the current local environment. No value was printed or copied and **no rotation or
  revocation was performed**; this remains an operator action and a release gate.
- **Dependencies (historical, superseded):** `docs/evidence/npm_audit_summary.json` reported 6
  vulnerable packages (2 moderate, 2 high, 2 critical). Those upgrades were subsequently applied;
  both current audits report **0 vulnerabilities** (see the 2026-11-24 sections below).
- **Registry (historical GHCR check):** the existing
  `ghcr.io/raphicsdigitalsolutions/smart-query-system:latest` package was confirmed present and
  anonymously pullable at the historical digest
  `sha256:417e017081a460adfe310236e13b3e117cb972c11c5c93370968aa866a2b0f0f`
  (`docs/evidence/ghcr_readonly_investigation.json`). That is not the current Docker Hub release
  digest (below). Publishing current local changes to GHCR still requires `write:packages`; no GHCR
  registry was modified. The current release disposition is **TECHNICAL RELEASE COMPLETE; FORMAL
  APPROVAL PENDING**.
- **Operator detail:** `docs/FINAL_RELEASE_BLOCKERS.md` and `docs/OPERATOR_ACTION_CHECKLIST.md`
  classify the original blockers with prerequisites, risks, exact commands and verification steps;
  `docs/RELEASE_READINESS.md` records which remain open.

## Deployment and provider status

> **Live hackathon deployment:** the FastAPI backend is on Vercel Hobby, the Next.js BFF is on Netlify
> Free, and PostgreSQL is hosted on Neon. The original URLs, deploy IDs, smoke results, serverless
> deviations, and unresolved gates are in `docs/HACKATHON_DEPLOYMENT_REPORT.md`. Use
> `docs/DEPLOYMENT_GUIDE.md` for operator-run build, migration, backup, rollback, HTTPS, and provider
> configuration steps. Live provider verification remains blocked.
>
> **Current verified state (2026-11-24):**
> - Vercel production deployment `dpl_CRo9kXq4CBL8p8oSaaAyKdSjNVoM` is `READY` (CLI source, production
>   alias `smart-query-backend.vercel.app`), serving backend version `1.0.0`. Only the daily
>   `0 0 * * *` escalation cron is configured; its hosted invocation is not verified.
> - Live backend smoke: `/health` 200 `healthy`, `/api/v1/status` 200 version `1.0.0`,
>   `/api/v1/status/database` 200 `connected`, `/api/v1/departments` 401 unauthenticated (expected).
> - Netlify public site `https://smart-query-routing-system.netlify.app` returned HTTP 200 at `/` and
>   `/api/health` (`Server: Netlify`). Authenticated deploy state and source sync are **NOT VERIFIED**:
>   no Netlify token was configured, the API returned 401 without credentials, and the live HTML uses
>   Turbopack chunks while current main builds with webpack after commit `75d6f16`. The recorded deploy
>   ID `6b02db1360e3188d7f1074c6` could not be authenticated or confirmed. No redeploy was performed;
>   the Netlify owner must confirm the deploy and redeploy from GitHub `main` if needed.
> - `release-v1` database read-only verification: Neon database `neondb`, URL fingerprint
>   `sha256_12 5d1fc726d19b`, host fingerprint `141f6064ec7f`, Alembic `feedf21773e1`, 17 public
>   tables, `departments=4`, `users=0`, `tickets=0`, `writes_performed=false`. Branch identity came from
>   the operator-provided, git-ignored `backend/.env.release_v1` filename; Vercel withholds sensitive
>   `DATABASE_URL` values and the Neon UI was unavailable. Direct Vercel-to-`.env` equality and old
>   production database state are **NOT** claimed.

## Migration considerations

- The Vite app stores its JWT only in module memory, so a reload signs the user out. The Next.js BFF
  stores it in an HttpOnly cookie, so a session survives reloads for up to the token lifetime
  (60 minutes by default in production; `tests/test_token_expiry.py` asserts this and isolates the
  test-only 1440-minute lifetime). Users must sign in once in Next.js because the Vite token is not
  shared.
- The BFF means browser requests are same-origin, so the existing FastAPI CORS allowlist for Vite
  ports does not need changing.
- Backend authorization remains authoritative; Next.js role guards only improve UX.
- The current `npm audit` and `npm audit --omit=dev` results are **0 vulnerabilities** in
  `frontend-next/` (`docs/evidence/npm_audit_final_2026-11-24.json`,
  `docs/evidence/npm_audit_prod_final_2026-11-24.json`); `frontend/` also reports 0 vulnerabilities.
  The earlier 6-package result in `docs/evidence/npm_audit_summary.json` is historical/superseded.

## Future development

See [docs/DEVELOPMENT_ROADMAP.md](docs/DEVELOPMENT_ROADMAP.md). Phase 7 added the integration and
packaging work, and the 2026-11-23 reconciliation added working-tree Playwright + axe E2E coverage.
Remaining items are formal institutional/governance sign-off, live provider verification (Google
OAuth, SMTP, Meta WhatsApp, real-user OpenAI BYOK), verification of the hosted escalation cron
invocation (only the daily schedule is verified), operator-controlled secret review/rotation,
Netlify deploy/source confirmation by the site owner, optional GHCR `write:packages` publication,
a real labelled evaluation dataset, and optional account features such as refresh tokens, password
reset and user CRUD. The Next.js 16.4.6/Zod 4.6.7/Vitest 4.1.12 dependency upgrades are already
applied and verified. True SSE/WebSocket push is not planned or claimed.

## Documentation

- [Project overview](docs/PROJECT_OVERVIEW.md)
- [Architecture](docs/ARCHITECTURE.md)
- [User guide](docs/USER_GUIDE.md)
- [Development roadmap](docs/DEVELOPMENT_ROADMAP.md)
- [API documentation](docs/API_DOCUMENTATION.md)
- [Agent evaluation harness](docs/AGENT_EVALUATION.md)
- [Deployment guide](docs/DEPLOYMENT_GUIDE.md)
- [Master requirements checklist](docs/MASTER_REQUIREMENTS_CHECKLIST.md)
- [Test report](docs/TEST_REPORT.md)
- [Authoritative completion matrix](docs/AUTHORITATIVE_COMPLETION_MATRIX.md)
- [Release readiness](docs/RELEASE_READINESS.md)
- [Secret audit and remediation plan](docs/SECRET_AUDIT_REMEDIATION_PLAN.md)
- [Final release blockers](docs/FINAL_RELEASE_BLOCKERS.md)
- [Operator action checklist](docs/OPERATOR_ACTION_CHECKLIST.md)
- [Final submission report](docs/FINAL_SUBMISSION_REPORT.md)
- [Final requirements traceability](docs/FINAL_REQUIREMENTS_TRACEABILITY.md)
- [Final demo guide](docs/FINAL_DEMO_GUIDE.md)
- [Final submission checklist](docs/FINAL_SUBMISSION_CHECKLIST.md)

## 2026-11-24 Final Submission Reconciliation

**Status: TECHNICAL RELEASE COMPLETE; FORMAL APPROVAL PENDING.** Technical release artifacts are
published and verified; formal institutional/governance approval and live provider verification remain
open. Historical `FAIL — DO NOT DEPLOY` verdicts elsewhere in this repository are superseded by this
section and `docs/RELEASE_READINESS.md`.

- **Git state:** Release evidence is anchored at `2cb5595ee7a38c85c63223079dc9d17a290ed089`. Chain:
  `b51dd31` → `7ad663e` (daily cron + Phase 1/2 evidence) → `eb30f92` (Docker Hub evidence) →
  `2cb5595` (live verification evidence) → `9399508` (documentation reconciliation) → submission-evidence
  commit recorded in `docs/evidence/final_submission_package_2026-11-24.json`. Working trees were clean
  after each pushed commit.
- **All 6 frontend dependency vulnerabilities** (`next`/`postcss`, `zod`, `vitest`, `@vitest/mocker`, `tinypool`) are remediated (`next@16.4.6`, `zod@4.6.7`, `vitest@4.1.12`, `eslint-config-next@16.4.6`); `npm audit` and `npm audit --omit=dev` both report **0 vulnerabilities** (`docs/evidence/npm_audit_final_2026-11-24.json`, `docs/evidence/npm_audit_prod_final_2026-11-24.json`).
- **Final verification re-run after upgrades:** backend **229 passed, 17 warnings in 410.30s (0:06:50)**, 0 failed/errors (`docs/evidence/final_backend_test.json`); `tsc --noEmit` / `eslint .` PASS, Vitest **3 passed**, `next build --webpack` **PASS** with Next.js 16.4.6 and **12/12** static pages, Playwright + axe **12 passed in 2.0m** with no serious/critical violations (`docs/evidence/e2e_axe_result.json`), disposable PostgreSQL backup/restore PASS, `docker compose -f docker-compose.db.yml config --quiet` and `docker compose -f docker-compose.yml config --quiet` PASS, `docker build --check .` no warnings, Alembic heads/current `feedf21773e1` and `alembic check` clean.
- **Single Combined Production Image (`Dockerfile` + `docker/supervisord.conf`):** Built (`python:3.11-slim` + `node:20-slim` + Supervisor, Next.js 16 + FastAPI in one container, non-root UID 10001, zero devDependencies/secrets), locally smoke-verified (healthy container, UID 10001, Supervisor backend+frontend RUNNING, backend health/login/api-health/session all HTTP 200 using disposable SQLite with email/WhatsApp/worker disabled). The image contains no `.env` or key files; pattern matches were Next.js docs/library strings only. Published to Docker Hub:
  - Public Repository: `https://hub.docker.com/r/raphicsdigitalsolutions/smart-query-system`
  - Pull Command: `docker pull raphicsdigitalsolutions/smart-query-system:latest`
  - Verified Tags & Digest: `latest` and `v1.0.0` both publish `sha256:2cf0a5dea54dffd643abf29a1fa7b72966899ff7235350b95fe1da793c9c2177`, matching local RepoDigests. Anonymous pull with a temporary empty Docker config exited 0 and the anonymous registry manifest returned HTTP 200 (`docs/evidence/phase4_docker_hub_release_2026-11-24.json`, `docs/evidence/docker_hub_anonymous_pull_2026-11-24.json`). The older `sha256:e9ed70810b3f9e5c6bb5ee1e7fb83847acb423c18a2bb506d9e83a5368450430` is stale.
- **Live and deployment verification (`docs/evidence/phase5_live_verification_2026-11-24.json`, `docs/evidence/release_v1_readonly_verification_2026-11-24.json`):** Vercel production deployment `dpl_CRo9kXq4CBL8p8oSaaAyKdSjNVoM` is READY; live backend smoke checks passed; the `release-v1` database was verified read-only with `writes_performed=false` as described above. Only the daily cron schedule existence is verified — hosted invocation/escalation effect, Google OAuth, SMTP, Meta WhatsApp, real-user OpenAI BYOK, university/institutional approval, hosted restore/malware scanner, and monitoring/retention are **NOT VERIFIED**.
- **Evidence index:** `docs/evidence/phase1_release_audit_2026-11-24.json`, `phase2_quality_verification_2026-11-24.json`, `phase4_docker_hub_release_2026-11-24.json`, `phase5_live_verification_2026-11-24.json`, `release_v1_readonly_verification_2026-11-24.json`, `docker_hub_anonymous_pull_2026-11-24.json`, `final_backend_test.json`, `e2e_axe_result.json`, `npm_audit_final_2026-11-24.json`, `npm_audit_prod_final_2026-11-24.json`.
- **University Submission Archive:** `submission/SmartQuerySystem_Final_Submission/` and `submission/SmartQuerySystem_Final_Submission.zip` (clean source, docs, 4 `.env.example` templates, 28 evidence files, and migrations with no non-template `.env` secrets, `node_modules`, `.venv`, `.e2e`, key files, or DB dumps). Source commit, SHA-256, and PDF hashes are recorded in `docs/evidence/final_submission_package_2026-11-24.json`; builder: `scripts/build_submission_package.ps1`. The `submission/` directory is gitignored and is a local deliverable.
