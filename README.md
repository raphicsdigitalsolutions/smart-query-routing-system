# Smart Query Routing & Email Automation System

**Project:** University Intelligent Communication Hub

A production-oriented university query-routing system. This checkout contains the Phase 1–4
FastAPI/PostgreSQL/React foundation, **Phase 5: a separate Next.js App Router frontend**,
**Phase 6: bounded staff-only AI assistance**, and **Phase 7: platform capabilities and integration
packaging**. Phase 7 includes BYOK OpenAI keys, approved knowledge, notifications with SMTP and
WhatsApp adapters, Google OAuth2, auto-routing/escalation, analytics, announcements, leave,
reports, audit, and full-stack Docker Compose packaging. The original Vite app is kept untouched as
the working reference.

> **No public deployment was performed.** Compose configuration was validated, but images were not
> built/pushed, no host was contacted, no DNS/provider setting was changed, and no data was modified
> by the packaging work. Live provider features require real credentials and provider approval.

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

The final full backend suite result is **187 passed** (17 pre-existing LangSmith deprecation
warnings). The current migration head is `feedf21773e1`, and the OpenAPI schema registers 41 paths
after adding ticket attachments and the WhatsApp verification handshake. Automated tests do not
call paid provider APIs. Exact commands and results are in `docs/TEST_REPORT.md`; the release decision
and operator actions are in `docs/RELEASE_READINESS.md`.

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
  code/config only; live provider verification and deployment remain pending.
- Google OAuth and BYOK were added in Phase 7. Refresh tokens, password reset, email verification
  and user-creation CRUD are still future work.
- Automated test suites for the Next.js frontend remain manual/live plus static checks.

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
  suite **187 passed**; frontend typecheck/lint/build passed; both Docker images built and smoke-tested;
  Compose config validation passed for both files. See `docs/TEST_REPORT.md` and
  `docs/RELEASE_READINESS.md`.

**Limits and blocked checks**

- **No public deployment was performed and public deployment is not approved.** The backend image
  was built locally; no image was pushed, no host was contacted, no DNS/TLS/provider setting was
  changed, and no production data was modified for this packaging work.
- Live SMTP, WhatsApp, Google OAuth and OpenAI evaluation checks are **blocked pending real
  credentials/provider setup** and were not performed.
- The evaluation harness uses a synthetic 24-record dataset. Its results test pipeline wiring and
  guardrails; they are not real university accuracy or performance.
- The Next.js app still has no committed e2e/accessibility test suite. Automated API, static UI,
  Docker build, and Compose checks are consolidated in `docs/TEST_REPORT.md`.
- BYOK shifts API cost to users; it does not satisfy the original zero-cost tooling constraint.

## Deployment and provider status

> **No public deployment was performed.** Use `docs/DEPLOYMENT_GUIDE.md` for the operator-run
> build, migration, backup, rollback, HTTPS and provider-configuration steps. Compose config and both
> local image builds passed; disposable-container health, migration, and BFF smoke checks are recorded
> in `docs/TEST_REPORT.md`. The full stack was not started against the existing production data
> volume, and live provider verification remains blocked.

## Migration considerations

- The Vite app stores its JWT only in module memory, so a reload signs the user out. The Next.js BFF
  stores it in an HttpOnly cookie, so a session survives reloads for up to the token lifetime
  (60 minutes by default). Users must sign in once in Next.js because the Vite token is not shared.
- The BFF means browser requests are same-origin, so the existing FastAPI CORS allowlist for Vite
  ports does not need changing.
- Backend authorization remains authoritative; Next.js role guards only improve UX.
- `npm audit` reported 3 advisories (1 moderate, 2 high): PostCSS advisories reached through
  Next.js 15 and a Zod advisory requiring Zod 4. `npm audit fix --force` would upgrade to Next.js 16
  and Zod 4, so it was not applied during Phase 5.

## Future development

See [docs/DEVELOPMENT_ROADMAP.md](docs/DEVELOPMENT_ROADMAP.md). Phase 7 added the integration and
packaging work; remaining items are live provider verification, operator-approved deployment, a
committed frontend e2e/accessibility suite, a real labelled evaluation dataset, and optional account
features such as refresh tokens, password reset and user CRUD.

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
