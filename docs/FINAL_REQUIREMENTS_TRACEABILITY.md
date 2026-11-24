# Final Requirements Traceability Matrix

**Baseline Date:** 2026-11-24  
**Authoritative Brief:** `AllProjectsS26.pdf` (pp. 30–31)  
**Repository Matrix Sources:** [AUTHORITATIVE_COMPLETION_MATRIX.md](file:///C:/Users/user/OneDrive/Desktop/SmartQuerySystem/docs/AUTHORITATIVE_COMPLETION_MATRIX.md), [MASTER_REQUIREMENTS_CHECKLIST.md](file:///C:/Users/user/OneDrive/Desktop/SmartQuerySystem/docs/MASTER_REQUIREMENTS_CHECKLIST.md)  
**Final Release Status:** **TECHNICAL RELEASE COMPLETE; FORMAL APPROVAL PENDING** — the live hackathon
demonstration and technical release artifacts are verified; formal institutional/governance sign-off,
live provider verification, hosted cron invocation, and Netlify source sync are not verified. See §4.

Status Mapping Used Below:
- **PASS:** Implemented cleanly and verified by executed local automated tests, builds, or rehearsals.
- **PARTIAL:** Implemented and offline/unit-tested cleanly, but live external provider/hosted execution remains unverified without production credentials.
- **BLOCKED:** Explicitly blocked by missing institutional governance approval, external credentials/scopes, or deliberate architectural substitution documented from the derived proposal.
- **FAIL:** Known defect or open security blocker (**0 items remaining after dependency remediation**).

---

## 1. Authoritative University Brief Functional Requirements (`FR-01` – `FR-14`)

| ID | Requirement | Implementation Modules | Verification Evidence | Submission Status | Notes / Conditions |
| --- | --- | --- | --- | --- | --- |
| FR-01 | Role-based login with Google OAuth2 | `api/routes/oauth.py`, `services/oauth_google.py`, `api/auth/google/route.ts`, `GoogleSignInButton.tsx` | `tests/test_oauth.py`, `tests/test_auth.py`, `e2e/auth.spec.ts` | **PARTIAL** | Offline token verification, linking, and password/RBAC flows **PASS**; live Google OAuth client/origin sign-in blocked on external credentials. |
| FR-02 | Multi-channel intake (web, email, WhatsApp) | `api/routes/tickets.py`, `api/routes/integrations.py`, `CreateTicketForm.tsx` | `tests/test_tickets.py`, `tests/test_integrations.py`, `e2e/tickets.spec.ts` | **PARTIAL** | Web form and token-gated webhook adapters **PASS** locally; live SMTP/Meta inbound webhooks unverified externally. |
| FR-03 | AI query classification & intent detection | `agents/nodes/classification.py`, `ticket_ai_analyses`, `AiAssistPanel.tsx` | `tests/test_ai_agents.py`, `tests/test_ai_api.py`, `tests/test_ai_consistency.py` | **PASS** | Mocked/offline structured classification & consistency tests pass; live inference requires user BYOK key. |
| FR-04 | Automatic routing to department or instructor | `services/auto_routing.py`, `services/instructor_routing.py` | `tests/test_tickets.py`, `tests/test_instructor_routing.py` | **PASS** | Deterministic department resolution + leave-aware, workload-balanced staff-only assignment. |
| FR-05 | AI draft replies with human approval | `agents/nodes/response_drafting.py`, `agents/services/agent_service.py` | `tests/test_ai_agents.py`, `tests/test_ai_api.py` | **PASS** | Enforces approved-knowledge citations, abstention, and explicit `approve-draft` publication gate. |
| FR-06 | Real-time query status tracking | `GET /tickets/{id}/updates` (ETag/304), `useTicketStatusPolling.ts` | `tests/test_ticket_updates.py`, Vitest `3 passed`, `e2e/tickets.spec.ts` | **PASS** | Conditional ETag/304 polling verified end-to-end (SSE/WebSocket push not implemented). |
| FR-07 | 24-hour auto-escalation for unresolved queries | `services/escalation.py`, `POST /tickets/escalation/sweep`, `backend/vercel.json` | `tests/test_escalation.py`, `tests/test_escalation_serverless.py`, `docs/evidence/phase5_live_verification_2026-11-24.json` | **PARTIAL** | Deterministic sweep & secret-protected cron endpoint PASS locally; live `0 0 * * *` daily schedule (exactly one Vercel cron) verified. Hosted invocation/escalation effect **NOT VERIFIED**. |
| FR-08 | Email & WhatsApp notifications | `services/notifications.py`, `email.py`, `whatsapp.py` | `tests/test_notifications.py`, `e2e/tickets.spec.ts` | **PARTIAL** | In-app notifications, dedupe, retries, internal-note/draft suppression **PASS**; live SMTP/Meta delivery blocked on creds. |
| FR-09 | HOD escalation and override capability | `services/tickets.py`, `TicketWorkflowPanel.tsx`, `TicketHistory.tsx` | `tests/test_tickets.py`, `tests/test_escalation.py`, `e2e/tickets.spec.ts` | **PASS** | Escalation/de-escalation audit history & deduplicated staff/HOD/admin notifications verified locally. |
| FR-10 | Admin analytics dashboard & charts | `api/routes/analytics.py`, `(protected)/analytics/page.tsx` | `tests/test_analytics.py`, `next build --webpack` | **PASS** | Role-scoped SQL aggregations and Recharts visualizations verified. |
| FR-11 | Broadcast announcements to students | `api/routes/announcements.py`, `(protected)/announcements/page.tsx` | `tests/test_announcements.py` | **PASS** | Role/department audience scoping and admin CRUD verified. |
| FR-12 | Export query reports to PDF & Excel | `api/routes/reports.py`, `services/reports.py`, `api/reports/[format]/route.ts` | `tests/test_reports.py` | **PASS** | ReportLab PDF, OpenPyXL XLSX headers/filters/permissions, and BFF streaming verified. |
| FR-13 | Instructor leave and auto-reply mode | `api/routes/leave.py`, `services/leave.py`, `(protected)/leave/page.tsx` | `tests/test_leave.py`, `tests/test_instructor_routing.py` | **PASS** | Active-window routing exclusion, exclusive end boundaries, and auto-replies verified (no formal approval workflow). |
| FR-14 | Query history & audit log for all activity | `services/audit.py`, `api/routes/audit.py`, `TicketHistory.tsx` | `tests/test_audit.py`, `tests/test_auth_audit.py`, `tests/test_escalation.py` | **PASS** | Covers ticket mutations, escalations, AI/knowledge/leave actions, and password register/login outcomes without secrets. |

---

## 2. Derived Proposal, Security, DevOps & Quality Gates

| Category / ID Range | Items Count | Status Breakdown | Verified Evidence |
| --- | ---: | --- | --- |
| Brief Tool / Cost / Supervision Constraints (`O-TOOL-01..07`, `O-COST-00`, `O-SUP-01`) | 9 | **5 PASS**, **4 BLOCKED** | `O-TOOL-01..04` & `O-SUP-01` **PASS**; `O-TOOL-05..07` & `O-COST-00` **BLOCKED** pending signed supervisor/university approval for OpenAI BYOK, FastAPI/SMTP/Meta, and hosting substitutions. |
| Derived Functional Requirements (`DFR-01..14`) | 14 | **11 PASS**, **3 PARTIAL** | `DFR-02..06`, `DFR-09..14` **PASS**; `DFR-01` (OAuth), `DFR-07` (hosted cron), `DFR-08` (live SMTP) **PARTIAL**. |
| Agent Guardrails & Data Model (`D-AGENT-00..06`, `D-ARCH-00`, `D-DATA-00..06`) | 15 | **10 PASS**, **5 PARTIAL** | `D-AGENT-01..04`, `D-AGENT-06`, `D-ARCH-00`, `D-DATA-01`, `D-DATA-04..06` **PASS**; `D-AGENT-00` (node naming deviation), `D-AGENT-05` (hosted cron), `D-DATA-00` (retention policy), `D-DATA-02/03` (formal policy classifiers) **PARTIAL**. |
| Security, Risk & QA (`D-SEC-01..08`, `D-RISK-00..05`, `D-QA-00..11`) | 26 | **14 PASS**, **9 PARTIAL**, **3 BLOCKED** | `D-QA-11` (**Dependency audit**) upgraded from **FAIL** to **PASS (`0 vulnerabilities`)**! `D-QA-00..06`, `D-QA-10`, `D-SEC-03`, `D-SEC-07`, `D-SEC-08`, `D-RISK-00..01` **PASS**; `D-SEC-01` (4 local secret candidates unrotated), `D-SEC-04` (university data policy), `D-RISK-05` (prod monitoring) **BLOCKED/PARTIAL**; live provider/cron/malware deployment checks **PARTIAL**. |
| Docker & Submission Governance (`D-DOCK-00..05`, `D-MVP-00..01`, `D-SUB-00`) | 9 | **4 PASS**, **2 PARTIAL**, **3 BLOCKED** | `D-DOCK-00`, `D-DOCK-01`, `D-DOCK-03` **PASS** (+ Next 16 container build/health re-verified); `D-MVP-00/01` **PARTIAL**; `D-DOCK-02` (local env secret rotation), `D-DOCK-04` (`write:packages` GHCR push), `D-DOCK-05` (prod monitoring), `D-SUB-00` (signed VU approval) **BLOCKED**. |

---

## 3. Aggregate Traceability Summary Across 87 Tracked Evaluation Rows

The counts below are the 2026-11-24 dependency-remediation snapshot; the final release verification
in §4 adds published-artifact and live-verification evidence without changing these row counts.

Combining the 14 Brief FRs + 9 Brief Constraints + 14 Derived FRs + 15 Agent/Data + 26 Security/Risk/QA + 9 Docker/Governance rows (**87 total rows**, reflecting the 2026-11-24 verification after dependency remediation):
- **PASS:** **44**
- **PARTIAL** *(implemented & locally verified; live external/hosted provider check pending)*: **23**
- **BLOCKED** *(requires owner credential rotation, `write:packages` scope, or signed university governance/deviation approval)*: **20** *(note: `O-TOOL-05..07`, `O-COST-00`, `D-SEC-01/04`, `D-DOCK-02/04/05`, `D-SUB-00`, and related provider/cost governance items)*
- **FAIL:** **0** *(previous `D-QA-11` `npm audit` failure is now **PASS**)*

---

## 4. Final release verification (2026-11-24)

**Status: TECHNICAL RELEASE COMPLETE; FORMAL APPROVAL PENDING.** Earlier `FAIL — DO NOT DEPLOY`
current-state verdicts are historical/superseded. Full detail and evidence index are in
`docs/RELEASE_READINESS.md` and `docs/TEST_REPORT.md` §10.

| Area | Verified | Not verified / caveat |
| --- | --- | --- |
| Git | `origin/main` `2cb5595ee7a38c85c63223079dc9d17a290ed089`; chain `b51dd31` → `7ad663e` → `eb30f92` → `2cb5595`; clean working tree after that commit. | No further git state changes claimed. |
| Quality gates | Backend **229 passed, 17 warnings in 410.30s (0:06:50)**, 0 failed/errors; Vitest **3 passed**; typecheck/lint PASS; `next build --webpack` (Next.js 16.4.6) PASS with **12/12** pages; Playwright + axe **12 passed in 2.0m**, no serious/critical violations; `npm audit` and `npm audit --omit=dev` **0 vulnerabilities**; both Compose `config --quiet` checks PASS; `docker build --check .` no warnings; Alembic heads/current `feedf21773e1`, `alembic check` clean. | Local rehearsals only for backup/restore and malware; hosted restore/scanner/monitoring/retention not verified. |
| Vercel backend | Production deployment `dpl_CRo9kXq4CBL8p8oSaaAyKdSjNVoM` READY, aliases `smart-query-backend.vercel.app` and `smart-query-backend-inforaphicsdigital-8444.vercel.app`; live `/health` 200 healthy, `/api/v1/status` 200 v1.0.0, `/api/v1/status/database` 200 connected, `/api/v1/departments` 401 (expected). Single daily cron `0 0 * * *` for `/api/v1/tickets/escalation/sweep`; current main's `backend/vercel.json` matches deployed config. | Deployment metadata names `b51dd31` with a dirty CLI working tree. Hobby permits at most once/day; hourly `0 * * * *` was invalid. **Schedule existence only; hosted invocation/escalation effect NOT VERIFIED.** |
| Netlify frontend | Public `https://smart-query-routing-system.netlify.app`: `/` and `/api/health` HTTP 200, `Server: Netlify`. | Authenticated deploy state/source sync NOT VERIFIED (no token, API 401; live Turbopack chunks vs main's webpack after `75d6f16`; deploy ID `6b02db1360e3188d7f1074c6` unconfirmed). Owner must confirm/redeploy if needed; no redeploy performed. |
| `release-v1` database | Read-only: `neondb`, URL `sha256_12 5d1fc726d19b`, host `141f6064ec7f`, Alembic `feedf21773e1`, 17 public tables, `departments=4`, `users=0`, `tickets=0`, `writes_performed=false`. | Branch identity comes from the git-ignored `backend/.env.release_v1` file name; Vercel withholds `DATABASE_URL` and Neon UI was unavailable — no direct Vercel-to-`.env` equality, no old production DB state claimed. |
| Docker Hub | `raphicsdigitalsolutions/smart-query-system:latest` and `:v1.0.0` both `sha256:2cf0a5dea54dffd643abf29a1fa7b72966899ff7235350b95fe1da793c9c2177`, matching local RepoDigests; anonymous pull (empty Docker config, exit 0) and manifest HTTP 200; healthy container, UID 10001, Supervisor backend+frontend RUNNING, backend health/login/api-health/session HTTP 200 with disposable SQLite (email/WhatsApp/worker disabled); no `.env`/key files in image. | The older `sha256:e9ed70810b3f9e5c6bb5ee1e7fb83847acb423c18a2bb506d9e83a5368450430` is stale. |

**NOT VERIFIED:** Google OAuth, SMTP, Meta WhatsApp, real-user OpenAI BYOK, hosted cron invocation,
university/institutional approval, hosted restore/malware scanner, monitoring/retention, Netlify
authenticated deploy state and source sync, Vercel-to-`.env.release_v1` database equality, and old
production database state. Formal production approval is not granted.

**Evidence:** `docs/evidence/phase1_release_audit_2026-11-24.json`,
`phase2_quality_verification_2026-11-24.json`, `phase4_docker_hub_release_2026-11-24.json`,
`phase5_live_verification_2026-11-24.json`, `release_v1_readonly_verification_2026-11-24.json`,
`docker_hub_anonymous_pull_2026-11-24.json`, `final_backend_test.json`, `e2e_axe_result.json`,
`npm_audit_final_2026-11-24.json`, `npm_audit_prod_final_2026-11-24.json`.
