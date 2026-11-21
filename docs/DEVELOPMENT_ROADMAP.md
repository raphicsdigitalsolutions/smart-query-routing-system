# Development Roadmap

Phases 1–6 below are historical, completed stages. Phase 7 is the current completed implementation and packaging stage. “Complete” means implemented and exercised locally or with deterministic tests; it does **not** mean live provider checks, image builds, or a public deployment were performed.

## Phase 1: Initial setup ✅

- [x] Define project structure and documentation.
- [x] Create FastAPI application with `/` and `/health`.
- [x] Add versioned API router (`/api/v1/status`).
- [x] Centralize settings with Pydantic Settings and `.env` support.
- [x] Configure CORS for the local Vite frontend.
- [x] Add structured error responses and exception handlers.
- [x] Create React + Vite + Tailwind shell with React Router and Axios.
- [x] Add responsive sidebar/topbar, dashboard and role placeholder pages.
- [x] Add backend smoke tests.

## Phase 2: Backend foundation ✅

- [x] Verify local backend and frontend startup and production build.
- [x] Keep configuration profiles and shared response conventions centralized.

## Phase 3: Database foundation ✅

- [x] Add `docker-compose.db.yml` with PostgreSQL 16 only, health check, restart policy and a
      persistent named volume.
- [x] Add root and backend `.env.example` files with placeholders (no real credentials).
- [x] Install psycopg 3 and Alembic; centralize DB settings in application config.
- [x] Implement SQLAlchemy 2.x engine, session factory, `get_db()` dependency and shutdown disposal.
- [x] Implement `User`, `Department`, `Ticket` and `Message` models with FKs, indexes, constraints
      and sensible defaults.
- [x] Configure Alembic to read the URL from settings and import all models into metadata.
- [x] Generate and apply the initial migration; verify upgrade, downgrade and no drift.
- [x] Add `GET /api/v1/status/database` with a safe 503 failure path.
- [x] Add tests for configuration, model imports/relationships/constraints and DB health handling.
- [x] Preserve the existing PostgreSQL container and volume; no tables were manually altered.

## Phase 4: Secure auth and core ticket management ✅

### Authentication and authorization

- [x] Add Argon2id password hashing and PyJWT access tokens.
- [x] Read the JWT signing key from `JWT_SECRET_KEY`; production fails closed when it is unset.
- [x] Implement `POST /api/v1/auth/register`, `POST /api/v1/auth/login` and `GET /api/v1/auth/me`.
- [x] Force public registration to create only active `student` accounts.
- [x] Add backend role dependencies for `student`, `staff`, `hod` and `admin`.
- [x] Add a dev-only first-admin CLI that rejects production, duplicates, weak passwords and
      plaintext defaults.
- [x] Document secure local admin provisioning.

### Ticket workflow

- [x] Implement ticket create, list, detail, patch, assign, messages and history endpoints.
- [x] Add pagination, filtering and indexed lookups.
- [x] Enforce the six-state lifecycle with role-aware transition validation.
- [x] Record status history, assignment history and audit logs transactionally.
- [x] Generate unique public references with collision retry.
- [x] Hide unauthorized tickets with 404 and hide internal notes from students.
- [x] Add department lookup and admin maintenance endpoints.

### Frontend and verification

- [x] Replace placeholder auth with real login/registration and an auth context.
- [x] Add protected routes, role-aware navigation, Bearer interceptor and sign-out.
- [x] Build real student, staff/HOD and admin ticket views plus ticket detail, replies, internal
      notes, assignment, status and history controls.
- [x] Add 45 isolated backend tests (auth, tickets, provisioning, models, health/config).
- [x] Apply Alembic revision `47ebce833eae` without recreating tables or deleting data.
- [x] Verify `alembic current`, `alembic check`, upgrade/downgrade and PostgreSQL table/columns.
- [x] Verify the frontend production build and live HTTP API flows; remove temporary smoke data.

## Phase 5: Next.js App Router migration ✅

### Scope and safety

- [x] Create a separate `frontend-next/` app; do not rewrite FastAPI or the working Vite frontend.
- [x] Preserve all Phase 1–4 endpoints, role rules, statuses, history/audit behavior and data.
- [x] Do not create application containers, provider deployment config or AI/email integrations as
      part of Phase 5; these were deferred to Phases 6–7 where applicable.

### Application foundation

- [x] Next.js 15 App Router with React 19, TypeScript strict mode, ESLint 9 and pinned dependencies.
- [x] Centralized config (`NEXT_PUBLIC_API_BASE_URL`, optional `API_BASE_URL`) and `.env.example`.
- [x] MUI 7 with SSR Emotion cache, Tailwind CSS v4 tokens, shadcn-style Radix primitives, Lucide
      icons and Sonner toasts.
- [x] Documented split: MUI for forms/dialogs/tables/navigation, shadcn wrappers for accessible
      primitives and small layout pieces.
- [x] Responsive `AppShell`, role-aware sidebar/topbar, loading/error/global-error/not-found screens.

### Auth and BFF

- [x] Route handlers for login, register, logout, `me`, session probe, health and catch-all backend
      proxy.
- [x] JWT stored only in an HttpOnly `smartquery_session` cookie; no `localStorage`/`sessionStorage`.
- [x] CSRF double submit with readable `smartquery_csrf` cookie and `x-csrf-token` header on unsafe
      methods, including logout.
- [x] Browser calls only same-origin Next.js routes; Bearer token is attached server-side, so backend
      CORS is unchanged.
- [x] Advisory client role guards plus server-side protected layout; backend authorization remains
      authoritative.

### Migrated features

- [x] Public registration and login, role-based post-login routing and sign-out.
- [x] Overview dashboard with ticket count, role summary and backend status card.
- [x] Student ticket submission with department/priority/category and filtered paginated ticket list.
- [x] Staff assigned queue, public replies, internal notes and allowed status transitions.
- [x] HOD department overview, assignment/reassignment, escalation and status controls.
- [x] Admin ticket overview, department create/update, assignable-user listing and assignment.
- [x] Ticket detail with conversation, internal-note privacy, status/assignment history and workflow
      panel.
- [x] Typed centralized API client, endpoint functions, typed errors, cancellation and no scattered
      URLs.

### Verification completed

- [x] `npm install` in `frontend-next`.
- [x] `npm run typecheck`, `npm run lint` and `npm run build` pass.
- [x] Live browser checks for all routes, registration/login/logout, role navigation and protected
      redirects.
- [x] Live ticket submission, staff replies/internal notes, HOD/admin assignment/status/escalation,
      admin department creation and internal-note privacy from the student view.
- [x] No unexpected browser console errors during the verified flows.
- [x] Vite production build passes and the Vite app still starts.
- [x] Backend `pytest -q` reports **45 passed**; `alembic current` is `47ebce833eae (head)`;
      `alembic check` reports no drift.
- [x] Temporary verification rows removed; database and named volume preserved.

### Known limitations

- Browser automation coverage was manual rather than a committed Next.js test suite.
- Existing Vite JWTs are module-memory only and are not shared; users sign in once in Next.js.
- `npm audit` reported 3 dependency advisories (PostCSS via Next.js 15 and Zod 3); no breaking
  forced upgrade to Next.js 16 / Zod 4 was applied in Phase 5.
- There is still no backend user-CRUD endpoint, refresh token flow or password reset.

### Intentionally not part of Phase 5 (later Phase 7 work)

- AI agents, OpenAI calls, SMTP/Gmail, WhatsApp, application Dockerfiles, Compose/deployment config
  and provider integrations were added later as Phase 6/7 code or packaging. Live provider checks
  and public deployment were still not performed.

## Phase 6: Bounded AI assistance ✅

### Scope and safety

- [x] Preserve all Phase 1–5 routes, role rules, ticket workflow, frontend apps and data.
- [x] Do not implement Gmail/WhatsApp, application containers, deployment config, refresh tokens,
      user CRUD or Phase 7+ work as part of Phase 6; Phase 7 later covered the integration and
      packaging items.
- [x] Keep `OPENAI_API_KEY` entirely server-side; never log, prompt, echo or return it.

### Agent architecture

- [x] Add pinned `langgraph==1.2.24` and `langchain-core==1.8.4`; use the existing official OpenAI
      SDK with structured-output parsing via Pydantic schemas.
- [x] Implement a fixed LangGraph workflow:
      `classification -> routing -> knowledge_research -> response_drafting -> validation`, with a
      conditional stop after a fatal classification error.
- [x] Add bounded retries (`AI_LLM_ATTEMPTS`), per-request timeouts, a monotonic workflow deadline,
      recursion limit, input/output caps and sanitized error categories. SDK-internal retries are off.
- [x] Add read-only tools: approved-knowledge JSON retrieval, backend-scoped routing lookups and
      deterministic ticket-text redaction before prompting.
- [x] Enforce trusted evidence and citations; abstain with no approved match and strip unverified
      source references.
- [x] Add `app/cli/test_openai.py` for an opt-in real connectivity probe that prints no secrets.

### Backend integration

- [x] Add `TicketAiAnalysis` and additive Alembic revision `b7d4e91c2a83`; no existing data, table,
      volume or database was recreated or deleted.
- [x] Add `POST /analyze`, `GET /analysis`, `POST /draft` and `POST /approve-draft` under
      `/api/v1/ai/tickets/{ticket_id}`.
- [x] Apply `require_staff_or_above` plus `get_accessible_ticket()` on every route; students get 403
      and invisible tickets get 404.
- [x] Keep all writes behind `AgentService`; the only public message path is explicit human approval
      through the existing `create_message()` service.
- [x] Record `ai.analysis_created`, `ai.analysis_failed` and `ai.draft_approved` audit rows; approval
      also records the existing `message.created` audit exactly once and is idempotent.

### Frontend integration

- [x] Add typed AI client endpoints using the existing same-origin BFF, CSRF handling and `apiFetch`.
- [x] Render a staff/HOD/admin-only `AiAssistPanel` on ticket detail with analysis, classification,
      priority/department/staff recommendations, sources, draft, regenerate, approve and
      loading/success/error states.
- [x] Clearly label recommendations as unconfirmed and drafts as not public until a staff member
      approves them.

### Verification completed

- [x] `python -m compileall -q app` passes.
- [x] Backend `pytest -q` reports **62 passed** (45 existing + 17 Phase 6 deterministic tests with
      mocked LLM responses; no automated paid API calls).
- [x] Tests cover structured-output validation/retry, deadline, redaction, graph order, routing
      fallback, source filtering/citations, abstention, student denial, invisible-ticket denial,
      approval idempotency, validation-failure publish block, one public message and audit rows.
- [x] `alembic upgrade head`, `alembic current` (`b7d4e91c2a83 (head)`) and `alembic check` pass.
- [x] Real OpenAI connectivity probe passed with `gpt-4o-mini` (one minimal request; no key output).
- [x] Live HTTP smoke check confirmed health, all four registered AI routes and unauthenticated 401.
- [x] Next.js `npm run typecheck`, `npm run lint` and `npm run build` pass.

### Known limitations

- No real labelled routing-accuracy dataset was added in Phase 6. Phase 7 added a deterministic
  synthetic harness, which is test infrastructure and not real university performance.
- Retrieval originally abstained until an approved knowledge file was configured; Phase 7 added
  database-backed approved knowledge documents with versioning and HOD/admin approval.
- The Next.js app still has no committed automated frontend test suite.
- AI output remains a recommendation/draft; staff must review correctness before approval.

### Intentionally not part of Phase 6 (later Phase 7 work)

- Gmail/SMTP or WhatsApp delivery, Docker images, deployment config, refresh tokens, password reset,
  user CRUD and full frontend test automation. The Phase 7 items below are code/config/package work;
  live provider verification and deployment were not performed.

## Phase 7: Platform capabilities, integrations and packaging ✅

Phase 7 completed the original integration and platform requirements as code and local packaging. It did **not** publish the system or verify any feature that needs a real external account.

### Defect fixes and authorization

- [x] Fixed the staff AI authorization defect caused by assignable-user lookup rejecting `staff`;
      staff can now run real analysis/draft workflows on assigned tickets and use routing lookups.
- [x] Consolidated role and visibility enforcement: public registration remains student-only,
      students see only their own tickets, invisible tickets return 404, student-only-denied AI/staff
      operations return 403, and staff/HOD/admin overrides remain role scoped.
- [x] Kept internal notes and unapproved AI drafts private and excluded from public replies,
      notifications and email.
- [x] Added per-user AI rate limiting through `AI_RATE_LIMIT_PER_MINUTE`, with an `ai_rate_limited`
      429 error. The final targeted regression test passed after the recorded full-suite run.

### Bring-your-own OpenAI key (BYOK)

- [x] Added per-user OpenAI key add, replace, validate and delete flows backed by
      `BYOK_ENCRYPTION_KEY` (Fernet) encryption at rest.
- [x] Exposed only a configured/not-configured status hint; the secret is never returned to the
      browser, logged, shared with another account, or placed in a frontend env file.
- [x] Production settings require `BYOK_ENCRYPTION_KEY`, forbid
      `ALLOW_GLOBAL_OPENAI_FALLBACK=true`, keep the global `OPENAI_API_KEY` empty, and fail closed
      when a user has no personal key.
- [x] Documented that BYOK moves API cost to the user and does not satisfy the original zero-cost
      tooling constraint.

### Agent evaluation harness

- [x] Added a versioned synthetic dataset (24 labelled queries) and a deterministic offline evaluator
      for intent, category, priority, department routing, retrieval, citations, unsupported claims,
      abstention, latency and token/cost metadata.
- [x] Added JSON and Markdown reports with dataset/model version metadata and the explicit warning
      that results are synthetic.
- [x] Added deterministic tests for dataset schema, report counts, abstention, versioning and the
      rule that live mode never silently falls back to the fake LLM.
- [ ] **Blocked:** live OpenAI evaluation requires explicit `--live` and a real `OPENAI_API_KEY`;
      it was not run pending credentials. Synthetic results are not real university performance.

### Approved knowledge management

- [x] Added HOD/admin knowledge management routes and UI for upload, review, approval, deactivation
      and version history of PDF/text/Markdown documents within configured type/size limits.
- [x] Restricted AI retrieval and citations to approved knowledge only; unapproved or deactivated
      documents are never retrieved, and unsupported answers abstain.

### Notifications and SLA

- [x] Added in-app notification history, SMTP email notifications and a Meta WhatsApp Cloud API
      adapter plus protected inbound intake routes using `X-Intake-Token`.
- [x] Covered submission, assignment, public replies, escalation/SLA breach and resolution;
      failures in external providers do not block ticket operations.
- [x] Added configurable `SLA_HOURS`, `ESCALATION_SWEEP_MINUTES`, automatic overdue escalation and
      audit/notification events, alongside manual HOD/admin escalation.
- [x] Preserved privacy rules: internal notes and unapproved AI drafts are never notified.
- [ ] **Blocked:** live SMTP and WhatsApp delivery/webhook checks require real provider credentials,
      recipient approval and provider configuration; they were not performed.

### Remaining original features

- [x] Added deterministic auto-routing and instructor assignment support with audited HOD/admin
      override, so students need not know the correct department.
- [x] Added optional Google OAuth2 sign-in through the same-origin BFF with the same backend RBAC;
      it does not grant extra permissions.
- [x] Added multi-channel web/email/WhatsApp intake metadata and protected inbound adapters.
- [x] Added admin analytics, targeted announcements, instructor leave/auto-reply, PDF/Excel report
      exports and a system-wide audit-log view/API for accountable history.
- [ ] **Blocked:** live Google OAuth verification requires a real Google Cloud client ID and exact
      provider configuration; it was not performed.

### Docker and deployment packaging

- [x] Added non-root backend and `frontend-next` Dockerfiles and a full-stack `docker-compose.yml`
      with `postgres`, `backend` and `frontend`, health checks, internal networking, migration-safe
      startup and no secrets baked into images.
- [x] Kept `docker-compose.db.yml` as the unchanged local PostgreSQL-only helper; the full-stack
      Compose project is `smartquerysystem` and reuses the external volume
      `smartquerysystem_smartquery_postgres_data`.
- [x] Added root/backend/frontend env examples covering BYOK, SMTP, WhatsApp, Google OAuth, SLA,
      rate limiting and upload controls.
- [x] Validated both Compose files with `docker compose -f ... config` (exit 0).
- [x] Both Docker images were built locally from the final source (`smartquery-backend:phase7` and
      `smartquery-frontend:phase7`). Container smoke testing found and fixed a missing-runtime-
      TypeScript defect in the frontend image; the corrected image passed health checks. Starting
      the full stack against the existing external database volume remains an operator-run check.
- [ ] **Public deployment is not approved and was not performed.** No host was contacted, no image
      was pushed, no DNS/TLS/provider setting was changed, and no data was modified by the packaging
      work.

### Testing and documentation

- [x] Migration head is `feedf21773e1` (Phase 7 platform capabilities); the additive chain is
      `44273a775ed8` → `47ebce833eae` → `b7d4e91c2a83` → `feedf21773e1`.
- [x] The OpenAPI schema registers **41 OpenAPI paths** after adding ticket attachments and the
      WhatsApp verification handshake.
- [x] The final full backend suite result is **187 passed** (17 pre-existing LangSmith deprecation
      warnings), including the AI rate-limit, attachment, and webhook regression tests.
- [x] Automated tests remain deterministic: mocked LLM responses and synthetic evaluation data; no
      paid provider calls are part of the automated suite.
- [x] Updated `README.md`, this roadmap, `docs/DEPLOYMENT_GUIDE.md`, `docs/USER_GUIDE.md`,
      `docs/AGENT_EVALUATION.md`, `docs/API_DOCUMENTATION.md`, `docs/ARCHITECTURE.md` and
      `docs/MASTER_REQUIREMENTS_CHECKLIST.md` for Phase 7.
- [x] `docs/TEST_REPORT.md` consolidates the executed backend, frontend, Docker, Compose, migration,
      and evidence commands, with blocked live checks listed explicitly.

### Follow-up work (not completed by Phase 7)

- [ ] Run live provider checks after credentials/approval are supplied: OpenAI live evaluation,
      SMTP delivery, Meta WhatsApp delivery/inbound verification and Google OAuth.
- [ ] Deploy the stack and publish images only after explicit approval; public deployment is not
      approved.
- [ ] Add committed Next.js e2e/accessibility tests, coverage thresholds and CI checks.
- [ ] Add a real labelled evaluation dataset and interpret live results with real privacy approval.
- [ ] Add refresh tokens, password reset and backend user CRUD if they are still desired.
- [x] Author `docs/TEST_REPORT.md` and re-run the full suite after the final regression addition.
