# Development Roadmap

> **Current verified release status (2026-11-24):** Technical release artifacts are published and verified; formal institutional/governance approval and live provider verification remain open. Authoritative evidence: `docs/evidence/phase5_live_verification_2026-11-24.json`. Current verdict: **TECHNICAL RELEASE COMPLETE; FORMAL APPROVAL PENDING**. Historical phase notes below retain their original counts and FAIL wording; the final reconciliation is at the end.

Phases 1–6 below are historical, completed stages. Phase 7 was the completed implementation and packaging stage. “Complete” means implemented and exercised locally or with deterministic tests. A live hackathon deployment was subsequently executed; see `docs/HACKATHON_DEPLOYMENT_REPORT.md` for actual endpoints, verification, and remaining governance gaps.

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

- Browser automation coverage was manual rather than a committed Next.js test suite during Phase 5;
  a working-tree Playwright + axe suite was added in the 2026-11-23 reconciliation below.
- Existing Vite JWTs are module-memory only and are not shared; users sign in once in Next.js.
- `npm audit` reported 3 dependency advisories in Phase 5 (PostCSS via Next.js 15 and Zod 3); no
  breaking forced upgrade was applied at that time. The later result was 6 vulnerabilities; all
  were remediated on 2026-11-24 (0 vulnerabilities) — see the reconciliation sections below.
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
- The Next.js app had no committed automated frontend test suite during Phase 6; this was later
  addressed by the Playwright + axe suite and Vitest polling-hook tests recorded in the
  2026-11-23 reconciliation below.
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
- [x] The FINAL full backend suite result is **229 passed, 17 warnings in 410.30s (0:06:50)**,
      0 failed/errors (17 pre-existing LangSmith deprecation warnings), including the AI rate-limit,
      attachment, webhook, FR-04b/FR-13 instructor-routing, FR-06 polling, FR-07 escalation,
      FR-14 auth-audit and token-expiry regression tests. Older 187/202/218/225 counts were
      intermediate runs.
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
- [x] A hackathon deployment and image publication were subsequently executed; public/institutional
      approval is still pending and the current verdict is **TECHNICAL RELEASE COMPLETE; FORMAL
      APPROVAL PENDING**.
- [x] Add working-tree Next.js e2e/accessibility tests — final result `12 passed (2.0m)`, no
      serious/critical axe violations. Coverage thresholds and CI checks remain future work.
- [ ] Add a real labelled evaluation dataset and interpret live results with real privacy approval.
- [ ] Add refresh tokens, password reset and backend user CRUD if they are still desired.
- [ ] Verify hosted escalation cron invocation (the daily schedule is verified) and configure
      `ESCALATION_CRON_SECRET` on the target host.
- [ ] Rotate/revoke the secrets identified in the redacted secret audit; no rotation was performed.
- [x] Next.js/Zod and test-toolchain upgrades behind the 6 npm advisories were applied and verified
      (0 vulnerabilities).
- [ ] Obtain GHCR `write:packages` permission before any GHCR publication; Docker Hub publication
      was completed separately.
- [x] Author `docs/TEST_REPORT.md` and re-run the full suite after the final regression addition.

## 2026-11-23 reconciliation (post-Phase 7 verification)

This section supersedes stale test/build/QA numbers in the historical phase notes above. It recorded
local evidence only, changed no credentials, registry, deployment or production data, and did
**not** revoke the then-current `FAIL — DO NOT DEPLOY` decision. The final 2026-11-24 release state
is in the last section of this roadmap.

- [x] FINAL full backend suite from `backend/`:
      `.\.venv\Scripts\python.exe -m pytest -q` → `229 passed, 17 warnings in 410.30s (0:06:50)`,
      0 failed/errors. Warnings are pre-existing LangSmith `asyncio.iscoroutinefunction`
      deprecations. Focused malware/attachment tests: `10 passed, 17 warnings in 7.63s`.
- [x] `frontend-next/e2e/` Playwright + axe suite: `npm run test:e2e` → `12 passed (2.0m)`;
      build passed with Next.js 16.4.6 webpack (`12/12` pages); no serious/critical axe violations
      on login, student workspace or ticket detail. Vitest `3 passed`; typecheck/lint PASS.
- [x] FR-04b/FR-13: deterministic, staff-only instructor routing (`test_instructor_routing.py`),
      active `InstructorLeave` windows excluded, HOD/admin never auto-assigned, overrides audited.
- [x] FR-06: conditional `GET /api/v1/tickets/{id}/updates` (ETag/304) and frontend
      `useTicketStatusPolling` hook; local-verified. This is **polling, not SSE/push**.
- [x] FR-07: secret-protected `POST /api/v1/tickets/escalation/sweep` and final daily
      `0 0 * * *` `backend/vercel.json` cron entry (`test_escalation_serverless.py`). The live cron
      list shows exactly that one job; **actual hosted invocation NOT VERIFIED**.
- [x] FR-14: password register/login success and failure audit events without passwords/secrets
      (`test_auth_audit.py`).
- [x] `test_token_expiry.py` asserts production 60-minute default; 1440 minutes is test-only.
- [x] Backup/restore rehearsal PASS in `docs/evidence/backup_restore_rehearsal.json`: disposable
      `postgres:16-alpine` at `127.0.0.1:55432`, schema hash
      `ed7d1ab744886956c3e35ddde4674a05b01da26ef8313199b2c741e35917664b`, record hash
      `00e07e9f6182a27c59db5e2b9b0d51055011c13029485c4647b9ba4cc994d419`, stale rows 1 → 0,
      container removed, production untouched.
- [x] Malware integration evidence `PASS_LOCAL_INTEGRATION_ONLY` in
      `docs/evidence/malware_scan_verification.json`: real ClamAV digest
      `sha256:64e30c0bf976198024deb3dc6d5cfe2485fb969c0f73549ba0fdb364b9469614`, clean `OK`/exit 0,
      in-container base64 EICAR `FOUND`/exit 1. A Windows-mounted EICAR fixture failed and is not
      claimed as a pass. `MALWARE_SCAN_ENABLED=false` by default; not deployed.
- [x] Secret audit (`docs/evidence/secret_audit.json`, `docs/SECRET_AUDIT_REMEDIATION_PLAN.md`):
      385 tracked files, 17 workspace potential secrets, 12 git-history potential secrets,
      453 docker-image potential secrets, 4 current-local-env matches; **no rotation/revocation**.
- [x] `npm audit` findings were remediated (`vitest@4.1.12`, `zod@4.6.7`, `next@16.4.6`,
      `eslint-config-next@16.4.6`); both `npm audit` and `npm audit --omit=dev` report 0
      vulnerabilities (`docs/evidence/npm_audit_post_remediation.json`). The 6-finding
      `docs/evidence/npm_audit_summary.json` is historical.
- [ ] GHCR publication remains blocked by missing `write:packages`; registry unchanged. Docker Hub
      image publication was verified; see the final reconciliation below for the current verdict.

## Final 2026-11-24 release reconciliation (current)

Authoritative evidence: `docs/evidence/phase5_live_verification_2026-11-24.json`. Current verdict: **TECHNICAL RELEASE COMPLETE; FORMAL APPROVAL PENDING**; all FAIL wording above is historical.

- Git: release-evidence commit `2cb5595ee7a38c85c63223079dc9d17a290ed089`; chain `b51dd31` → `7ad663e` (daily cron + Phase 1/2 evidence) → `eb30f92` (Docker Hub evidence) → `2cb5595` (live verification evidence); clean working tree after that commit.
- Backend: Vercel `dpl_CRo9kXq4CBL8p8oSaaAyKdSjNVoM` READY/production/source CLI with aliases `smart-query-backend.vercel.app` and `smart-query-backend-inforaphicsdigital-8444.vercel.app` (Vercel-login protected; public HTTP not verified); deployed metadata commit `b51dd31` with dirty CLI tree, deployed config already has the daily cron and current main matches. Live cron list: one `0 0 * * *` job; invocation NOT VERIFIED. `/health`, `/api/v1/status`, `/api/v1/status/database` HTTP 200; `/api/v1/departments` HTTP 401 expected.
- Frontend: Netlify public root and `/api/health` HTTP 200, but authenticated deploy state and source sync NOT VERIFIED (no token; API 401). Live Turbopack chunks vs current webpack build after `75d6f16` prevent a "matches main" claim; deploy `6b02db1360e3188d7f1074c6` unconfirmed. Owner: confirm/redeploy from GitHub main; no redeploy performed.
- Database: `release-v1` read-only — `neondb`, URL fingerprint `5d1fc726d19b`, host fingerprint `141f6064ec7f`, Alembic `feedf21773e1`, 17 public tables, 4 departments, 0 users, 0 tickets, no writes. Branch identity from the git-ignored `backend/.env.release_v1` file name; Vercel sensitive values withheld and Neon UI unavailable, so hosted equality not verified. Original production database previously checked read-only and not modified; not re-checked here.
- Image: Docker Hub `raphicsdigitalsolutions/smart-query-system:latest` / `:v1.0.0` digest `sha256:2cf0a5dea54dffd643abf29a1fa7b72966899ff7235350b95fe1da793c9c2177` (replaces stale `sha256:e9ed708…`); anonymous pull exit 0 with empty Docker config, manifest HTTP 200; smoke healthy, UID 10001, Supervisor backend+frontend RUNNING, 4 HTTP checks 200 with disposable SQLite/no external integrations, no `.env` or key files in image.
- NOT VERIFIED: Google OAuth, SMTP, Meta WhatsApp, real-user BYOK, hosted cron invocation, university approval, hosted restore/malware scanner, monitoring/retention.
