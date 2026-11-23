# Authoritative Completion Matrix

**Project:** Smart Query Routing & Email Automation System  
**Repository:** `C:\Users\user\OneDrive\Desktop\SmartQuerySystem`  
**Matrix date:** 2026-11-22  
**Reconciled:** 2026-11-23 — local evidence for polling, auth audit events, restore rehearsal, malware local integration, browser E2E/accessibility, the redacted secret audit, the six-package `npm audit`, and the read-only GHCR investigation is incorporated below. "Local verified" never implies live provider, hosted scheduler, registry publication, or governance approval; the `FAIL — DO NOT DEPLOY` decision in `docs/RELEASE_READINESS.md` is unchanged. Operator detail is in `docs/FINAL_RELEASE_BLOCKERS.md` and `docs/OPERATOR_ACTION_CHECKLIST.md`.  
**Authority:** Where wording conflicts, the original university brief wins. The in-repo derived proposal is a technical blueprint, **not institutional approval**.

## Sources

1. Original university brief: `C:\Users\user\Downloads\AllProjectsS26.pdf`, pages 30–31.
2. Derived in-repo proposal: `Smart_Query_Routing_Agentic_AI_Project_Proposal_Premium.pdf`, Version 1.1, November 2026.
3. Existing reconciliation: `docs/MASTER_REQUIREMENTS_CHECKLIST.md`, `docs/RELEASE_READINESS.md`, `docs/TEST_REPORT.md`, `docs/HACKATHON_DEPLOYMENT_REPORT.md`.
4. Final release-blocker reconciliation: `docs/FINAL_RELEASE_BLOCKERS.md`, `docs/OPERATOR_ACTION_CHECKLIST.md`, `docs/evidence/ghcr_readonly_investigation.json`, `docs/evidence/npm_audit_summary.json`.

## Status vocabulary

- **PASS** — implemented and verified by an executed local test, build, migration check, or reproducible offline rehearsal.
- **FAIL** — required behavior is missing or a known defect remains.
- **BLOCKED** — cannot be completed locally because a specific credential, provider, approval, or destructive decision is missing.
- **NOT VERIFIED** — implementation exists, but live/external or end-to-end evidence is still unavailable.

No requirement is removed or downgraded. A PASS on the offline path never implies live provider verification.

---

## 1. Original university brief — exact functional requirements

Source: `AllProjectsS26.pdf`, page 30. Exact wording preserved.

| ID | Original wording | Current implementation | Missing implementation | Required tests | External dependencies | Approval dependencies | Final status |
|---|---|---|---|---|---|---|---|
| FR-01 | Role-based login with Google OAuth2 authentication (All Roles) | Argon2/JWT auth, Google ID-token verification, `user_oauth_accounts` linking, BFF cookie/CSRF flow | Live Google verification only | `tests/test_oauth.py`, role/auth tests | Real Google OAuth client ID/secret and configured origin | None for offline code; provider setup for live use | NOT VERIFIED |
| FR-02 | Multi-channel query submission via email, web form, and WhatsApp (Student) | Web create API/form, token-gated email and WhatsApp inbound adapters, `tickets.channel` | Live provider delivery/webhook registration only | `tests/test_integrations.py`, `tests/test_tickets.py` | SMTP credentials; Meta Cloud API token/phone ID | None for offline code; provider setup for live use | NOT VERIFIED |
| FR-03 | AI-powered query classification and intent detection (System) | LangGraph classification node, structured output, persisted `ticket_ai_analyses` | No missing local function | `tests/test_ai_agents.py`, `tests/test_ai_api.py`, `tests/test_agent_evaluation.py` | BYOK OpenAI key for live inference | None for offline code | PASS |
| FR-04 | Automatic routing to correct department or instructor (System) | `auto_routing.py` department resolution + `instructor_routing.py` deterministic staff assignment | Subject-matter expertise/capacity routing not modeled | `tests/test_tickets.py`, `tests/test_instructor_routing.py`, `tests/test_integrations.py` | None | None for implemented behavior | PASS |
| FR-05 | AI-generated draft reply suggestions for staff (All Staff) | Bounded drafting/validation agents, approved-knowledge citations, staff approval gate | No missing local function | `tests/test_ai_agents.py`, `tests/test_ai_api.py` | BYOK OpenAI key for live inference | None for offline code | PASS |
| FR-06 | Real-time query status tracking for students (Student) | On-demand status/history APIs, ticket timeline UI, conditional snapshot endpoint (`GET /tickets/{id}/updates` with ETag/304), and `useTicketStatusPolling` hook in ticket detail | True push/SSE not implemented; polling is conditional client refresh, not WebSocket/SSE | `tests/test_tickets.py`, `tests/test_ticket_updates.py`, `frontend-next/src/hooks/useTicketStatusPolling.test.tsx`, E2E polling case in `frontend-next/e2e/tickets.spec.ts` (11 E2E tests pass) | None | None | PASS (polling) |
| FR-07 | 24-hour auto-escalation for unresolved queries (System) | Deterministic sweep, `SLA_HOURS`, repeat-safe audit/notifications, admin endpoint, secret-protected cron trigger (`POST /tickets/escalation/sweep`), hourly `backend/vercel.json` cron entry | Live cron execution on deployed host not verified; `ESCALATION_CRON_SECRET` must be configured in target environment | `tests/test_escalation.py`, `tests/test_escalation_serverless.py` | Configured cron scheduler + `ESCALATION_CRON_SECRET` on target host | Hosting/secret configuration approval for live automation | NOT VERIFIED (code ready, live unverified) |
| FR-08 | Email and WhatsApp notification system (All Roles) | `notifications.py`, event templates, in-app rows, fake-provider tests, retry/dedupe metadata | Live SMTP/Meta delivery only | `tests/test_notifications.py` | SMTP; Meta Cloud API | Provider setup for live use | NOT VERIFIED |
| FR-09 | HOD escalation and override capability (HOD) | Department-scoped HOD patch, assignment, escalation/de-escalation status history & audit trail (`previous`/`new`, actor, timestamp), deduplicated permission-scoped escalation notifications, `TicketHistory` Escalations card | No missing local function | `tests/test_tickets.py`, `tests/test_escalation.py`, `tests/test_analytics.py`, `frontend-next/e2e/tickets.spec.ts` | None | None | PASS |
| FR-10 | Admin analytics dashboard with charts and reports (Admin) | Role-scoped analytics API, Recharts UI, PDF/XLSX exports | No missing local function | `tests/test_analytics.py`, `tests/test_reports.py` | None | None | PASS |
| FR-11 | Broadcast announcement to students (Admin) | Admin/HOD announcement CRUD, audience visibility | No missing local function | `tests/test_announcements.py` | None | None | PASS |
| FR-12 | Export query reports to PDF and Excel (Admin / HOD) | ReportLab/XLSX exporters and BFF streaming route | No missing local function | `tests/test_reports.py` | None | None | PASS |
| FR-13 | Instructor leave and auto-reply mode (Instructor) | Leave CRUD, active-window auto-reply, routing exclusion, manual-assignment reply | Formal approval-state workflow not modeled | `tests/test_leave.py`, `tests/test_instructor_routing.py`, `tests/test_notifications.py` | None | University decision if approval workflow is required | PASS |
| FR-14 | Query history and audit log for all system activity (Admin) | Audit service, ticket/status/assignment history, admin audit API, AI/leave/knowledge audit events, password register/login success/failure audit events | No missing local auth-event implementation identified; live identity-provider session semantics remain environment-specific | `tests/test_audit.py`, `tests/test_auth_audit.py`, `tests/test_tickets.py` | None | None | PASS |

## 2. Original brief — tools, cost, and supervision

| ID | Original wording / requirement | Current implementation | Missing implementation | Required tests | External dependencies | Approval dependencies | Final status |
|---|---|---|---|---|---|---|---|
| O-TOOL-01 | Development Environments / IDEs: VS Code, PyCharm Community Edition, Postman | Project runs from VS Code-compatible folders; API is Postman-testable; PyCharm is optional local tooling | No code deliverable | Build/API checks | Local IDE installation | None | PASS |
| O-TOOL-02 | Python 3.11+, JavaScript ES6+, HTML5/CSS3, SQL (PostgreSQL) | Python 3.11+ backend, TypeScript/React frontend, PostgreSQL-compatible SQLAlchemy models | No code deliverable | Test suite, typecheck, build | Runtime installation | None | PASS |
| O-TOOL-03 | FastAPI, React.js, Tailwind CSS, LangChain, SQLAlchemy, Pydantic | FastAPI, React/Next.js, Tailwind, LangGraph/LangChain ecosystem, SQLAlchemy, Pydantic | Framework name substitution documented | Tests + builds | None | None | PASS |
| O-TOOL-04 | Recharts / Chart.js analytics visualizations | Recharts implemented | No code deliverable | Frontend build | None | None | PASS |
| O-TOOL-05 | Google Gemini API free tier; Claude API free tier | OpenAI BYOK substitution | Gemini/Claude provider not used | AI tests | Provider credentials | Derived proposal approved OpenAI substitution | BLOCKED |
| O-TOOL-06 | n8n self-hosted; Gmail API; Baileys; Google Sheets API | FastAPI services, SMTP, Meta adapter, local PostgreSQL audit/notification tables | Named tools not used | Notification/integration tests | Provider credentials | Derived proposal replaced tools | BLOCKED |
| O-TOOL-07 | PostgreSQL / Supabase free tier; Render.com free tier; Vercel free | PostgreSQL-compatible Neon, Vercel backend, Netlify frontend, local Docker/Compose | Named Supabase/Render stack not used | Deployment smoke already recorded | Hosting accounts | Existing deployment executed; governance still open | BLOCKED |
| O-COST-00 | Zero cost, free-tier tools and APIs | BYOK avoids a global paid key; hosted stack currently on free tiers | Cannot guarantee zero AI cost when a user supplies a paid key | Config/BYOK tests | User's own API key | University acknowledgement required | BLOCKED |
| O-SUP-01 | Supervisor: Saima Jamil; `Saima.jamil@vu.edu.pk`; Teams `saima.jamil1988@outlook.com` | Recorded in source brief and reports | No code deliverable | Document check | None | None | PASS |

## 3. Derived proposal — exact functional requirement wording

Source: derived proposal page 4. These IDs conflict with the original brief; included for completeness only.

| ID | Derived wording | Current implementation | Missing implementation | Required tests | External dependencies | Approval dependencies | Final status |
|---|---|---|---|---|---|---|---|
| DFR-01 | Authentication — Secure sign-in and role-based access | Argon2/JWT/RBAC + OAuth | Live Google check | Auth tests | Google credentials | None for offline | NOT VERIFIED |
| DFR-02 | Query intake — Web form creates a ticket and reference ID | Implemented | None | Ticket tests | None | None | PASS |
| DFR-03 | AI classification — Suggests category, intent, urgency, language and confidence | Implemented | None locally | AI tests | BYOK | None | PASS |
| DFR-04 | Routing — Assigns or recommends a department using approved rules | Department + instructor routing implemented | Skills/capacity not modeled | Routing tests | None | None | PASS |
| DFR-05 | AI response draft — Creates a grounded draft; staff approval is required | Implemented | None | AI tests | BYOK | None | PASS |
| DFR-06 | Student tracking — Students see their own ticket status and timeline | Timeline/history UI, conditional snapshot endpoint, frontend polling hook with change detection, E2E polling case | Push/SSE not implemented; polling only | `tests/test_ticket_updates.py`, `frontend-next/src/hooks/useTicketStatusPolling.test.tsx`, `frontend-next/e2e/tickets.spec.ts` | None | None | PASS (polling) |
| DFR-07 | Escalation — Overdue cases are flagged under configurable SLA rules | Deterministic sweep, admin endpoint, secret-protected cron endpoint, Vercel cron config | Live scheduler execution not verified | `tests/test_escalation.py`, `tests/test_escalation_serverless.py` | Scheduler/host secret | Hosting approval for cron | NOT VERIFIED |
| DFR-08 | Notifications — Email notifications for configured ticket events | Offline path implemented | Live SMTP | Notification tests | SMTP | Provider setup | NOT VERIFIED |
| DFR-09 | Manager override — Authorized manager can reassign/escalate with audit record | Implemented for assign, status, escalation, and de-escalation with actor/timestamp/previous-new audit & notification fanout | None | Role, escalation, and notification tests | None | None | PASS |
| DFR-10 | Analytics — Ticket volume, categories, response time, backlog and exports | Implemented | None | Analytics/report tests | None | None | PASS |
| DFR-11 | Announcements — Admin broadcasts to selected audiences | Implemented | None | Announcement tests | None | None | PASS |
| DFR-12 | Audit trail — Records key actions, actor, time and related ticket | Implemented for ticket/AI/knowledge/leave and password auth register/login success/failure events | No missing local auth-event implementation identified | `tests/test_audit.py`, `tests/test_auth_audit.py` | None | None | PASS |
| DFR-13 | Staff availability — Staff can set leave/availability; routing can respect it | Implemented for active leave windows | Formal approval state | Leave/routing tests | None | University decision | PASS |
| DFR-14 | History — Authorized users can review permitted case history | Implemented | None | Ticket history tests | None | None | PASS |

## 4. Derived proposal — non-functional, security, testing, and submission requirements

| ID | Original wording / requirement | Current implementation | Missing implementation | Required tests | External dependencies | Approval dependencies | Final status |
|---|---|---|---|---|---|---|---|
| D-RBAC-00 | Every protected operation must be checked by the backend against the authenticated user, role and permitted scope; hiding a button in React is not authorization | Backend role dependencies and service scope checks | None known | Role/isolation tests | None | None | PASS |
| D-AGENT-00 | Five bounded agents with approved tools and human-control boundaries | Five-node graph; SLA follow-up is a deterministic service outside the graph | Exact node-name parity | Agent/evaluation tests | BYOK | Documented deviation | PASS |
| D-AGENT-01 | Low-confidence or sensitive cases go to staff review | Validation node and approval gate | None | Agent tests | BYOK | None | PASS |
| D-AGENT-02 | Backend validates policy; staff can override | Backend routing/assignment + manual override | None | Routing/override tests | None | None | PASS |
| D-AGENT-03 | Abstain if no reliable source exists; never invent policy | Approved-knowledge repository + citation validation | None | Knowledge/agent tests | BYOK for live drafts | None | PASS |
| D-AGENT-04 | External sending requires explicit staff approval | Approval gate before public message | None | AI API tests | None | None | PASS |
| D-AGENT-05 | Deterministic scheduler controls SLA; agent cannot close tickets | Deterministic escalation service; no agent close tool; secret-protected cron endpoint and hourly cron config exist locally | Live serverless auto-trigger execution not verified | `tests/test_escalation.py`, `tests/test_escalation_serverless.py` | Host scheduler + secret | Hosting approval | NOT VERIFIED |
| D-AGENT-06 | Model must not execute arbitrary SQL, run shell commands, or send messages directly | Read-only tools + backend-owned side effects | None | Agent security tests | None | None | PASS |
| D-ARCH-00 | Channels → FastAPI core → AI services → PostgreSQL → worker/SLA | Modular monolith implemented | Dedicated worker only on long-running hosts | Architecture/build checks | None | None | PASS |
| D-DATA-00 | Relational, auditable, role-scoped entities | Models and migrations exist | Formal retention policy enforcement | Model/API tests | None | University data policy | NOT VERIFIED |
| D-DATA-01 | Every ticket receives a unique public reference; internal IDs are not auth tokens | `TKT-...` unique reference | None | Ticket tests | None | None | PASS |
| D-DATA-02 | AI priority is a suggestion; emergency/safety follow deterministic rules | Deterministic status/SLA rules; no autonomous priority application | Explicit emergency policy model | AI/ticket tests | None | University policy if required | NOT VERIFIED |
| D-DATA-03 | Low-confidence, conflicting or sensitive cases require human review | Internal drafts and approval gate | Explicit sensitivity classifier | Agent tests | BYOK | University policy if required | NOT VERIFIED |
| D-DATA-04 | Internal notes never shown to students | Service filtering + notification suppression | None | Ticket/notification tests | None | None | PASS |
| D-DATA-05 | Closure requires authorized staff action and resolution summary | Implemented | None | Ticket tests | None | None | PASS |
| D-DATA-06 | Assignment/status/escalation/override events are logged | Implemented for assignment, status, manual/auto escalation, de-escalation, and password auth register/login success/failure events | No missing local auth-event implementation identified | `tests/test_audit.py`, `tests/test_auth_audit.py`, `tests/test_tickets.py`, `tests/test_escalation.py` | None | None | PASS |
| D-SEC-01 | Secrets in env/secrets manager; never commit to Git | Env examples, ignore rules, BYOK encryption, redacted `scripts/secret_audit.py` triage | Owner-approved rotation/revocation of 4 current-local matches; no values printed or changed | Release-hardening tests, `docs/evidence/secret_audit.json`, `docs/SECRET_AUDIT_REMEDIATION_PLAN.md` | Secret manager | Operator rotation | BLOCKED |
| D-SEC-02 | HTTPS, secure sessions, hashing, backend role checks | HTTPS at host; HttpOnly/Secure cookies; Argon2/RBAC | Live provider recheck | Auth/BFF tests | Hosting TLS | Deployment governance | NOT VERIFIED |
| D-SEC-03 | Send only necessary content to AI provider | Deterministic redaction | Ticket text still sent | Redaction tests | BYOK | None | PASS |
| D-SEC-04 | Define access, retention, deletion and backup policies before real student records | Backup/restore docs; executed disposable rehearsal PASS (`docs/evidence/backup_restore_rehearsal.json`); no production data touched | Formal policy sign-off only; local restore rehearsal complete | Restore rehearsal evidence in `docs/evidence/backup_restore_rehearsal.json` | None | University data-policy approval | BLOCKED |
| D-SEC-05 | Validate file types and sizes; keep files outside web root; scan where practical | Extension/signature/size validation; outside-web-root storage; optional fail-closed ClamAV hook with real local integration | Scanner not enabled or deployed; `MALWARE_SCAN_ENABLED=false` by default; Windows-mounted EICAR fixture failed (exit 2) and is not a pass | `tests/test_attachments.py`, `tests/test_malware_scan_service.py`, `tests/test_attachment_malware.py`, `docs/evidence/malware_scan_verification.json` (`PASS_LOCAL_INTEGRATION_ONLY`) | ClamAV/scanner in target environment | Security approval | NOT VERIFIED |
| D-SEC-06 | Idempotency, retries and delivery status to prevent duplicate emails | Notification rows with attempts/status/dedupe | Live provider verification | Notification tests | SMTP/Meta | Provider setup | NOT VERIFIED |
| D-SEC-07 | Log agent decisions/tool calls without secrets or excessive PII | Sanitized telemetry and audit details | None | Agent/BYOK tests | None | None | PASS |
| D-SEC-08 | Rate limits, timeouts, max steps, budgets, manual fallback | Durable per-user rate limit + bounded calls + staff fallback | None | AI API tests | None | None | PASS |
| D-RISK-00 | Wrong classification mitigated by thresholds/rules/human review/evaluation | Evaluation dataset + deterministic routing + review | None | Evaluation tests | BYOK for live | None | PASS |
| D-RISK-01 | Hallucinated policy answer mitigated by approved knowledge and abstention | Implemented | None | Knowledge/agent tests | BYOK for live | None | PASS |
| D-RISK-02 | Provider limits mitigated by queues/retries/sandbox | Retries/delivery status; no external queue | Queue not added | Notification tests | Provider sandbox | Architecture change if queue required | NOT VERIFIED |
| D-RISK-03 | API cost growth mitigated by usage tracking/budgets/limits | Token metadata + BYOK + rate limits | Hard spend caps per user not modeled | AI/BYOK tests | Provider billing controls | University cost policy | NOT VERIFIED |
| D-RISK-04 | Sensitive data exposure mitigated by minimization/access/encryption/retention/privacy review | Access controls + encryption + redaction | Formal retention/privacy review | Security tests | None | University privacy approval | NOT VERIFIED |
| D-RISK-05 | Deployment outage mitigated by health checks/backups/monitoring/logs/rollback | Health checks + docs + live smoke + local restore rehearsal PASS | Monitoring system and different-host restore still missing | `docs/evidence/backup_restore_rehearsal.json`, backup test + ops checks | Monitoring provider | Deployment governance | FAIL |
| D-QA-00 | Student cannot access another student's ticket by changing an ID | 404-hiding ownership checks | None | Ticket isolation tests | None | None | PASS |
| D-QA-01 | Staff can access only cases within authorized scope | Assigned-ticket scoping | None | Role tests | None | None | PASS |
| D-QA-02 | Classification safely handles ambiguous/malformed input | Structured validation + tests | None | AI tests | BYOK for live | None | PASS |
| D-QA-03 | Routing follows configured rules; staff override available and audited | Implemented | None | Routing/audit tests | None | None | PASS |
| D-QA-04 | Knowledge drafts cite sources; missing evidence causes abstention | Implemented | None | Agent tests | BYOK for live | None | PASS |
| D-QA-05 | AI replies remain drafts until explicit staff approval | Implemented | None | AI API tests | None | None | PASS |
| D-QA-06 | Unauthorized tool calls rejected; retries do not create duplicate tickets/emails | Read-only tools + notification dedupe | None | AI/notification tests | None | None | PASS |
| D-QA-07 | Overdue escalation repeat-safe and auditable | Implemented locally; cron trigger endpoint tested | Live serverless auto-trigger execution not verified | `tests/test_escalation.py`, `tests/test_escalation_serverless.py` | Host scheduler | Hosting approval | NOT VERIFIED |
| D-QA-08 | Provider downtime does not lose ticket data; failed jobs can be retried | Transactional ticket persistence; delivery rows | Queue-backed retry not present | Notification failure tests | Provider sandbox | Architecture change if queue required | NOT VERIFIED |
| D-QA-09 | A backup can be restored and Docker stack starts on another machine | Docs, prior disposable container smoke, executed local restore rehearsal PASS | Different physical host not exercised | `docs/evidence/backup_restore_rehearsal.json`, Compose config/container smoke | Docker/Postgres | None for disposable test | NOT VERIFIED (local restore PASS) |
| D-QA-10 | New frontend E2E/accessibility tests are required before claiming a full product QA pass | Working-tree Playwright + axe suite; `npm run test:e2e` 12 passed in 1.5m after successful build; no serious/critical axe violations on login, student workspace, ticket detail, plus manual escalation/de-escalation history and staff notification flow | No missing local test; dependency audit findings are tracked separately | `frontend-next/e2e/{auth,tickets,a11y}.spec.ts`, `npm run test:e2e` | Browser test runner | None | PASS |
| D-QA-11 | Dependency vulnerabilities must be remediated before release | Upgraded `vitest@4.1.12`, `zod@4.6.7`, `next@16.4.6`, and `eslint-config-next@16.4.6`; post-remediation evidence in `docs/evidence/npm_audit_post_remediation.json` | None (`0 vulnerabilities` remaining) | `npm audit`, `npm audit --omit=dev`, typecheck, lint, Vitest (`3 passed`), `next build --webpack`, Playwright (`12 passed`) | Registry connectivity used for upgrade | None remaining | PASS |
| D-DOCK-00 | backend/Dockerfile and frontend/Dockerfile | Present | No missing local function | Docker build | Docker | None | PASS |
| D-DOCK-01 | docker-compose.yml for local multi-service testing | Present | No missing local function | `docker compose config` | Docker | None | PASS |
| D-DOCK-02 | .dockerignore and .env.example with no real secrets | Present; redacted audit stores no values | Owner review/rotation of 4 current-local matches; image findings are code/dependency patterns | `docs/evidence/secret_audit.json`, secret scan | None | Operator rotation | BLOCKED |
| D-DOCK-03 | Health checks, persistent DB volume, migration command, startup ordering | Present | No missing local function | Compose/health checks | Docker | None | PASS |
| D-DOCK-04 | Tagged images and registry push instructions | Docs reference GHCR image; local builds possible | Publication of current local changes blocked by missing `write:packages`. The existing `.../smart-query-system:latest` package is confirmed present and anonymously pullable at digest `sha256:417e017081a460adfe310236e13b3e117cb972c11c5c93370968aa866a2b0f0f` (`docs/evidence/ghcr_readonly_investigation.json`); no push was attempted | Read-only manifest/blob checks, `docker buildx imagetools inspect` | GHCR credentials with `write:packages` | Release governance | BLOCKED (package existence resolved) |
| D-DOCK-05 | Production secrets, domain/TLS, monitoring, backup/restore, rollback docs | Provider-independent docs exist; live deployment executed separately | Signed deviations and formal approval | Docs + provider checks | Hosting credentials | Deployment governance | BLOCKED |
| D-MVP-00 | Role login, submission, tracking, staff queue, triage, routing recommendation, grounded draft, approval, email notifications, audit, basic admin | Implemented offline | Live provider verification | Full suite | Providers | Provider setup | NOT VERIFIED |
| D-MVP-01 | Defer WhatsApp, complex autonomous agents, advanced analytics, broad rollout | WhatsApp adapter exists but live deferred | None | Integration tests | Meta credentials | University rollout approval | NOT VERIFIED |
| D-SUB-00 | Proposal is not institutional approval; confirm final requirements/data policies/integrations/model/hosting budget/deliverables with supervisor | Recorded in checklist and release docs | Formal signed approval | Document check | None | Supervisor/university | BLOCKED |

## 5. Current aggregate disposition

| Area | Status | Evidence / reason |
|---|---|---|
| FR-01 Google OAuth | NOT VERIFIED | Offline verification and RBAC tests pass; live Google credentials absent. |
| FR-02 Multi-channel intake | NOT VERIFIED | Web + mocked adapters pass; live SMTP/Meta credentials absent. |
| FR-03 AI classification | PASS | Agent, AI API, consistency, and evaluation tests pass. Final full backend suite: **229 passed, 17 warnings in 264.12s** (earlier runs: 225 passed in 265.61s; 218 passed in 235.04s; focused malware/attachment run 10 passed in 7.63s). Warnings are pre-existing LangSmith deprecations. |
| FR-04 / FR-04b routing | PASS | Department + deterministic instructor routing tests pass; staff-only, leave-aware, no HOD/admin auto-assignment, no approval workflow. |
| FR-05 AI drafts/approval | PASS | Approval gate and unapproved-draft suppression tests pass. |
| FR-06 live tracking | PASS (polling) | Conditional ETag/304 snapshot endpoint, frontend polling hook, and E2E polling case pass; SSE/push still not implemented. |
| FR-07 auto-escalation | NOT VERIFIED | Deterministic sweep, secret-protected cron endpoint, hourly cron config, and serverless tests verified locally; live hosted cron execution unverified. |
| FR-08 notifications | NOT VERIFIED | Offline delivery tests pass; live providers absent. |
| FR-09–FR-12 | PASS | HOD, analytics, announcements, exports tested. |
| FR-13 leave exclusion | PASS | Routing exclusion and auto-reply preservation tests pass; active leave windows only. |
| FR-14 full audit | PASS | Password register/login success/failure audit events added and tested without passwords or secrets. |
| Backup/restore rehearsal | PASS (local) | Disposable `postgres:16-alpine` rehearsal PASS; schema hash `ed7d1ab744886956c3e35ddde4674a05b01da26ef8313199b2c741e35917664b`, record hash `00e07e9f6182a27c59db5e2b9b0d51055011c13029485c4647b9ba4cc994d419`, stale row 1→0, container removed, production untouched. Formal policy sign-off still open. |
| Malware scanning | NOT VERIFIED (local integration only) | Real ClamAV fixtures clean OK/exit 0 and Eicar FOUND/exit 1; 10 focused tests pass; `MALWARE_SCAN_ENABLED=false` by default, not deployed. Windows-mounted EICAR fixture failed (exit 2) and is not a pass. |
| Secret audit | BLOCKED | Triage complete with redacted fingerprints: tracked 307, workspace potential 16, Git-history potential 12, container-image potential 453, current-local-env matches 4. Classified as actual-secret candidates (4), test fixtures, false positives/safe samples and historical code-pattern matches. No rotation/revocation; live provider checks blocked. |
| GHCR image | PASS (existence/pull) / BLOCKED (publication) | Existing `smart-query-system:latest` package is anonymously pullable and digest-matched to `sha256:417e017081a460adfe310236e13b3e117cb972c11c5c93370968aa866a2b0f0f`; current local changes are not published and no registry write occurred. |
| Security | BLOCKED (deps PASS / live & secrets open) | Dependency audit remediated to **0 vulnerabilities** (`next@16.4.6`, `zod@4.6.7`, `vitest@4.1.12`). Live provider checks, 4 local secret reviews/rotations, GHCR `write:packages`, and signed deviations remain open. |
| Testing | PASS (local) | Post-remediation backend **229 passed (292.01s)**, Vitest **3 passed**, Playwright + Axe **12 passed (2.2m)**, `typecheck`/`lint`/`next build --webpack` **PASS**, `npm audit` & `--omit=dev` **0 vulnerabilities**. |
| Release governance | BLOCKED | Production/public FAIL and signed deviations unresolved despite live hackathon deployment. |

This matrix was reconciled against 2026-11-23 local evidence; it does not grant release approval.
