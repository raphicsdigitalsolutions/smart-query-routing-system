# Final University Submission Report — Smart Query Routing & Email Automation System

**Project Title:** Smart Query Routing & Email Automation System (University Intelligent Communication Hub)  
**Repository:** `https://github.com/raphicsdigitalsolutions/smart-query-routing-system`  
**Submission Baseline Date:** 2026-11-24  
**Authoritative Brief:** Virtual University Final Year Project Brief (`AllProjectsS26.pdf`, pp. 30–31; Supervisor: Saima Jamil)  
**Submission Readiness Verdict:** **PASS for Local / University Demonstration** · **Production Public Release: CONDITIONAL / BLOCKED pending external provider credentials, owner secret rotation, and institutional governance sign-off**

---

## 1. Project Overview

Universities receive high volumes of academic, technical, financial, and administrative student queries across fragmented channels (email, web forms, messaging apps, and walk-ins). Manual triage causes delayed responses, misrouted tickets, repeated follow-ups, poor status visibility for students, and weak accountability for Heads of Department (HODs) and administrators.

The **Smart Query Routing & Email Automation System** solves this with a role-scoped, auditable, full-stack web platform:
- **Students** submit queries via a web portal (or email/WhatsApp webhook intake adapters), attach documents, receive a unique `TKT-...` tracking reference, view conversation updates via conditional ETag polling, and receive notifications.
- **Staff / Instructors** manage assigned queues, collaborate with staff-only internal notes (strictly hidden from students), execute bounded LangGraph/OpenAI AI triage and knowledge-grounded reply drafting using their **personal encrypted OpenAI API key (BYOK)**, and approve drafts before publication. Staff can also configure instructor leave windows with automatic routing exclusion and auto-replies.
- **HODs** oversee department queues, manually reassign or escalate/de-escalate tickets with full audit trails, approve governed institutional knowledge documents, and track department analytics.
- **Administrators** manage departments, view system-wide analytics, export PDF/Excel reports, broadcast announcements, trigger SLA escalation sweeps, and inspect append-only audit logs.

---

## 2. Problem Statement & Objectives

### Problem Statement
Manual university helpdesk workflows suffer from misrouting, lack of SLA accountability, ungrounded ad-hoc responses, exposure of internal staff deliberations, and absence of end-to-end audit trails.

### Primary Objectives Achieved
1. **Unified Multi-Role Communication Hub:** Four strict RBAC roles (`student`, `staff`, `hod`, `admin`) enforced in FastAPI dependencies and service ownership checks, fronted by a Next.js App Router BFF that keeps JWTs in `HttpOnly` cookies.
2. **Deterministic + Governed AI Routing:** Automated department keyword routing + deterministic, load-balanced, leave-aware instructor assignment (`app/services/instructor_routing.py`), paired with a 5-node bounded LangGraph AI assistant (`classification -> routing -> knowledge_research -> response_drafting -> validation`) that cites only HOD/admin-approved knowledge (`DatabaseKnowledgeRepository`) and abstains when evidence is missing.
3. **Strict Human-in-the-Loop & Privacy Boundaries:** Internal staff notes never reach students or notifications; unapproved AI drafts are never published or emailed; ticket text is PII-redacted before AI calls; and personal OpenAI BYOK keys are Fernet-encrypted at rest with zero global production fallback.
4. **Accountability, SLA & Reporting:** Six-state ticket lifecycle, transactional status/assignment/escalation history, append-only audit logs (including authentication events), 24-hour deterministic SLA escalation, Recharts analytics, and PDF/XLSX exports.

---

## 3. Architecture & Technology Stack

```text
Browser
  └── Next.js 16 App Router (frontend-next, React 19, TypeScript strict)
        ├── Same-origin BFF (/api/auth/*, /api/backend/[...path], /api/reports/[format], /api/health)
        ├── HttpOnly session cookie (smartquery_session) + double-submit CSRF (smartquery_csrf / x-csrf-token)
        └── Advisory client role guards + MUI 7 + Tailwind CSS v4 + Radix UI + Recharts
              │ (server-side Authorization: Bearer)
              ▼
FastAPI Backend (backend, Python 3.12+/3.14 venv, SQLAlchemy 2.x, Pydantic v2)
  ├── 41 OpenAPI paths across 17 versioned routers (/api/v1/*) + /health
  ├── Argon2id password hashing, HS256 JWTs, optional Google Identity Services OAuth2
  ├── 5-node LangGraph workflow + official OpenAI SDK (per-user Fernet-encrypted BYOK)
  ├── SMTP & Meta WhatsApp Cloud API delivery adapters + token-gated inbound webhooks
  ├── Optional fail-closed ClamAV malware scanner hook + outside-web-root attachment storage
  └── Deterministic 24h SLA escalation service + secret-protected cron trigger (/tickets/escalation/sweep)
              │
              ▼
PostgreSQL 16 (Alembic migration head: feedf21773e1; SQLite in-memory/file for isolated tests/demo)
```

*(A legacy Phase 4 Vite + React reference app is also preserved cleanly in `frontend/` with zero vulnerabilities.)*

---

## 4. Implemented Features Summary

- **Authentication & RBAC:** Student self-registration (no self-escalation), Argon2id password hashing, JWT bearer/cookie BFF flow, CSRF double-submit protection, dev-only guarded admin provisioning CLI, password register/login audit logging, and optional Google OAuth2 token exchange.
- **Core Ticket Lifecycle:** Unique `TKT-...` reference IDs, `new -> assigned -> in_progress -> waiting_for_student -> resolved -> closed` workflow, mandatory resolution summary, 404 ownership hiding for unauthorized IDs, public vs. internal messages, validated PDF/TXT/MD attachments with SHA-256 checksums, and conditional ETag/`304` live status polling (`useTicketStatusPolling`).
- **Routing, Leave & Escalation:** Keyword department routing, deterministic leave-aware staff-only instructor assignment, instructor leave CRUD + active-window auto-replies, manual HOD/admin escalation & de-escalation with `TicketHistory` Escalations panel and deduplicated permission-scoped notifications, plus deterministic 24h SLA escalation sweep & cron endpoint.
- **Governed AI & BYOK:** Fernet-encrypted per-user OpenAI API keys (`/settings/api-keys`), strict fail-closed `402 ai_personal_key_required`, PII redaction, bounded 5-node LangGraph triage & drafting, HOD/admin approved versioned knowledge (`pypdf`/text ingestion), inline `kb-{id}-v{ver}` citations, and explicit human draft approval (`approve-draft`).
- **Analytics, Notifications & Operations:** Department/global analytics API + Recharts dashboard, ReportLab PDF & OpenPyXL Excel report exports, role/department-scoped announcements, in-app notification center, and admin audit viewer.

---

## 5. Dependency Security Remediation (Completed 2026-11-24)

All 6 previously open frontend dependency vulnerabilities (`2 moderate, 2 high, 2 critical` across 10 GHSAs) were remediated cleanly in `frontend-next/` without `--force`:
1. **`vitest` `3.2.4 → 4.1.12`** (plus explicit dev dependencies `vite@^7.3.8` & `@testing-library/dom@^10.4.2`): eliminated critical `vitest`, `tinypool`, and `@vitest/mocker` advisories while keeping Node 20 compatibility for [frontend-next/Dockerfile](file:///C:/Users/user/OneDrive/Desktop/SmartQuerySystem/frontend-next/Dockerfile). Fixed `react-hooks/refs` in [useTicketStatusPolling.ts](file:///C:/Users/user/OneDrive/Desktop/SmartQuerySystem/frontend-next/src/hooks/useTicketStatusPolling.ts).
2. **`zod` `3.25.76 → 4.6.7`**: eliminated high `GHSA-mrhx-c7xc-m3w5`; updated BFF validation schemas in [login/route.ts](file:///C:/Users/user/OneDrive/Desktop/SmartQuerySystem/frontend-next/src/app/api/auth/login/route.ts) and [register/route.ts](file:///C:/Users/user/OneDrive/Desktop/SmartQuerySystem/frontend-next/src/app/api/auth/register/route.ts) to Zod v4 `z.email()` and `z.flattenError()`.
3. **`next` & `eslint-config-next` `15.5.29 → 16.4.6`**: eliminated moderate/high `next` + nested `postcss@8.4.31` advisories (`GHSA-qx2v-qp2m-jg93`, `GHSA-6g55-p6wh-862q`, `GHSA-fxqj-rqcc-2cmp`, `GHSA-r28c-9q8g-f849`). Migrated [eslint.config.mjs](file:///C:/Users/user/OneDrive/Desktop/SmartQuerySystem/frontend-next/eslint.config.mjs) to native ESLint 9 flat config and [layout.tsx](file:///C:/Users/user/OneDrive/Desktop/SmartQuerySystem/frontend-next/src/app/layout.tsx) to `@mui/material-nextjs/v16-appRouter`. Configured [package.json](file:///C:/Users/user/OneDrive/Desktop/SmartQuerySystem/frontend-next/package.json) `build` / `pretest:e2e` scripts with `next build --webpack` because Next 16's default Turbopack hit `TurbopackInternalError` spawning the PostCSS worker on Windows/OneDrive.
- **Verified Post-Remediation Audits:** Both `npm audit` and `npm audit --omit=dev` in `frontend-next/`, plus `npm audit` in `frontend/`, report **`0 vulnerabilities`**.

---

## 6. Security Design Summary

- **Credential & Key Hygiene:** Passwords hashed with Argon2id; JWT stored in `HttpOnly`, `SameSite=Lax`, `Secure` (prod) cookie via same-origin BFF with CSRF double-submit verification.
- **Mandatory BYOK & Fail-Closed Prod Validation:** `Settings` validator rejects startup in `ENVIRONMENT=production` with `DEBUG=true`, `ALLOW_GLOBAL_OPENAI_FALLBACK=true`, placeholder/weak JWT or Fernet keys, placeholder DB creds, non-TLS external DB URLs, or wildcard CORS.
- **Upload & Malware Defense:** Extension/size validation (`pdf`, `txt`, `md`, 5 MiB default), outside-web-root storage, SHA-256 metadata, and fail-closed ClamAV subprocess hook (`503` if scanner unavailable/times out, `422` if infected; disabled by default).
- **Redacted Secret Audit:** `docs/evidence/secret_audit.json` identified 4 current-local-env fingerprint candidates (`OPENAI_API_KEY`, `BYOK_ENCRYPTION_KEY`, `VERCEL_OIDC_TOKEN`, `DATABASE_URL`) requiring owner review/rotation — left unrotated per non-destructive policy.

---

## 7. Testing Methodology & Verified Results

| Suite / Check | Scope | Result |
| --- | --- | --- |
| Backend Full Suite | `backend\.venv\Scripts\python.exe -m pytest -q` (SQLite isolated DB) | **229 passed**, 17 pre-existing LangSmith warnings (`292.01s`) |
| Backend Compile & Migrations | `compileall` + `alembic heads` + PostgreSQL rehearsal `alembic upgrade head` | **PASS** — clean chain to `feedf21773e1 (head)` |
| Frontend Audit (`npm audit` & `--omit=dev`) | All `frontend-next` and `frontend` deps | **0 vulnerabilities** (`743` total / `211` prod) |
| Frontend Typecheck & Lint | `npm run typecheck` (`tsc --noEmit`), `npm run lint` (`eslint .`) | **PASS** — 0 errors, 0 warnings |
| Frontend Unit Tests | `npm run test` (`vitest run` v4.1.12) | **3 passed** (`useTicketStatusPolling.test.tsx`) |
| Frontend Production Build | `npm run build` (`next build --webpack` v16.4.6) | **PASS** — all app & API routes built cleanly |
| Playwright + Axe E2E | `npm run test:e2e` (Chromium + `@axe-core/playwright`) | **12 passed (2.2m)** — 0 serious/critical a11y violations |
| Disposable PostgreSQL Restore | `scripts/backup_restore_rehearsal.ps1` on `postgres:16-alpine` | **PASS** — schema & record SHA-256 hashes matched, prod untouched |
| Docker Compose & Image Builds | `docker compose config --quiet` + `docker build` (backend & Next 16 frontend) | **PASS** — both images built and passed isolated container health + BFF smoke (`/api/health` 200, `/login` 200, `/api/auth/session` 200, `/api/backend/auth/me` 401) |
| Single Combined Docker Hub Image | `Dockerfile` (`python:3.11-slim` + `node:20-slim` + Supervisor) | **PASS** — published cleanly to `https://hub.docker.com/r/raphicsdigitalsolutions/smart-query-system` (`latest`, `v1.0.0`, digest `sha256:e9ed70810b3f9e5c6bb5ee1e7fb83847acb423c18a2bb506d9e83a5368450430`; anonymous pull + combined BFF/FastAPI/Postgres smoke verified) |
| Local ClamAV Integration | `clamav/clamav:stable` + 10 pytest cases (`PASS_LOCAL_INTEGRATION_ONLY`) | **PASS locally** — clean `OK` (0), EICAR `FOUND` (1), fail-closed hooks |

> [!NOTE]
> **Windows Sandbox Observation:** Running `TestClient(app)` or Playwright inside the restricted Windows AppContainer sandbox (`BypassSandbox: false`) blocked `127.0.0.1` loopback `socket._fallback_socketpair()` / local port connections. Executing with standard host loopback access (`BypassSandbox: true`) completed every test cleanly with zero application code changes.

---

## 8. Installation & Execution Instructions

1. Copy `.env.example` / `backend/.env.example` / `frontend-next/.env.example` to `.env` / `backend/.env` / `frontend-next/.env.local` and supply non-placeholder local secrets.
2. Start PostgreSQL (`docker compose -f docker-compose.db.yml up -d postgres`) or use the offline SQLite demo script (`powershell -ExecutionPolicy Bypass -File .\scripts\start_local_demo.ps1`).
3. Backend: from `backend/`, activate `.venv`, run `alembic upgrade head`, and start `uvicorn app.main:app --port 8000` (or `pytest -q` with `DEBUG=false`).
4. Frontend: from `frontend-next/`, run `npm ci`, `npm run build` (uses Webpack), and `npm run start`.

---

## 9. Known Limitations, Live Blockers & Future Improvements

- **Live External Providers (Not Verified Here):** Real Google OAuth client ID/origin, live SMTP credentials & verified `MAIL_FROM`, live Meta WhatsApp Cloud API tokens/webhook, real-user OpenAI live key smoke test, hosted FR-07 Vercel cron (`ESCALATION_CRON_SECRET`), and GHCR new-tag publication (`write:packages`).
- **Owner Actions & Governance:** Review/rotate the 4 local fingerprint matches in `docs/evidence/secret_audit.json`; obtain signed university approval for OpenAI BYOK / Meta / FastAPI tool substitutions and zero-cost policy disclosure.
- **Future Enhancements:** Add WebSocket/SSE push notifications, refresh tokens/password reset UI, real labelled institutional dataset evaluation, and hosted ClamAV sidecar deployment.
