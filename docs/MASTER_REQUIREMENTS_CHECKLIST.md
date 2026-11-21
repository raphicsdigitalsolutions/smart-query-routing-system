# Master Requirements Checklist — Phase 7

This document is the single source of truth for Phase 7. Every requirement from the original university brief, the derived in-repo proposal, Phases 1–6.1, and Phase 7 is mapped to implementation, database changes, tests, documentation, and an explicit status.

Statuses use exactly these values:

- **Complete and verified** — implemented and exercised by an actual test, build, migration check, or live local run.
- **Implemented but not fully verified** — code/config exists; live external provider or credential-dependent verification is still required.
- **Pending** — not implemented.
- **Blocked** — cannot be completed without a specific external dependency; reason is stated.

> Audit completed. The authoritative original brief is `C:\Users\user\Downloads\AllProjectsS26.pdf`. The in-repo `Smart_Query_Routing_Agentic_AI_Project_Proposal_Premium.pdf` is a derived blueprint with conflicting FR IDs; where they conflict, the original brief wins and the difference is recorded below. Final test/build evidence is consolidated in `docs/TEST_REPORT.md`; security remediation, redacted secret findings, and the PASS/FAIL release decision are in `docs/RELEASE_READINESS.md`. Section M records audit corrections to statuses that were previously overstated.

---

## A. Original proposal and development requirements

### A.1 Authoritative original university brief

Source: `C:\Users\user\Downloads\AllProjectsS26.pdf`, pages 30–31 (the duplicate `(1)` file is byte-identical).

| ID | Exact requirement | Backend implementation | Frontend implementation | Database changes | Tests | Documentation | Status | Evidence / notes |
|---|---|---|---|---|---|---|---|---|
| A-FR-01 | Role-based login with **Google OAuth2** authentication | `api/routes/oauth.py`, `services/oauth_google.py`, offline ID-token verification, `UserOauthAccount` linking | `GoogleSignInButton`, BFF `POST /api/auth/google` | `user_oauth_accounts` | `tests/test_oauth.py` | `API_DOCUMENTATION.md`, `DEPLOYMENT_GUIDE.md` | Implemented but not fully verified | Offline token verification, account linking, disabled-state denial, and privilege-escalation refusal are tested. Live Google verification is blocked until a real OAuth client ID is configured. |
| A-FR-02 | Multi-channel query submission via **email, web form, and WhatsApp** | Web ticket API plus token-gated `integrations/email/inbound` and `integrations/whatsapp/inbound` | Web create form; no separate provider UI needed | `tickets.channel` | `tests/test_integrations.py` | `API_DOCUMENTATION.md`, `DEPLOYMENT_GUIDE.md` | Implemented but not fully verified | Channel field, mapped-student lookup, fail-closed intake token, and auto-route are tested. Live provider delivery is blocked until real SMTP/Meta credentials are configured. |
| A-FR-03 | AI-powered query classification and intent detection | `agents/nodes/classification.py`, LangGraph workflow | `AiAssistPanel` | `ticket_ai_analyses` | `tests/test_ai_agents.py`, `tests/test_ai_api.py` | `ARCHITECTURE.md`, `API_DOCUMENTATION.md` | Complete and verified | Uses OpenAI rather than the brief's Gemini/Claude suggestion; provider substitution is documented. |
| A-FR-04 | Automatic routing to correct department **or instructor** | deterministic `auto_routing.py`; audited department auto-route; manual assignment to staff/instructor | department field, assignable-user UI, auto-route option | `tickets.auto_routed`, audit rows | `tests/test_tickets.py::test_auto_routing_selects_department_and_audits`, `tests/test_integrations.py::test_inbound_ticket_can_auto_route` | `ARCHITECTURE.md`, `USER_GUIDE.md` | Implemented but not fully verified | Automatic **department** routing is implemented and tested. See A-FR-04b for the instructor-specific gap. |
| A-FR-04b | Automatic routing directly to a named instructor | Not implemented; department auto-route plus manual assignment exists | assignment UI | none | none | `USER_GUIDE.md` | Pending | Explicit audit sub-item: the original wording allows “department or instructor”; only department auto-selection is automated. Instructor choice remains a human assignment decision. |
| A-FR-05 | AI-generated draft reply suggestions for staff | `response_drafting.py`, `agent_service.py`, approval boundary | `AiAssistPanel` | `ticket_ai_analyses` | `tests/test_ai_agents.py`, `tests/test_ai_api.py` | `API_DOCUMENTATION.md` | Complete and verified | Human approval gate preserved; unapproved drafts are internal only. |
| A-FR-06 | Real-time query status tracking for students | status/history APIs | ticket table/detail/history | history tables | `tests/test_tickets.py` | `USER_GUIDE.md` | Implemented but not fully verified | On-demand status/history tracking is tested. See A-FR-06b for the live-refresh gap. |
| A-FR-06b | Live polling/SSE status refresh | Not implemented | no `setInterval`/SSE polling found | none | none | — | Pending | Explicit audit sub-item: students can refresh/reload to see updates; there is no push or automatic polling channel. |
| A-FR-07 | 24-hour auto-escalation for unresolved queries | deterministic sweep, `SLA_HOURS`, repeat-safe audit/notifications, production-only background task | HOD/admin escalation controls visible | `tickets.escalated_at` | `tests/test_escalation.py`, `tests/test_tickets.py` | `ARCHITECTURE.md`, `USER_GUIDE.md` | Complete and verified | Offline deterministic sweep and admin-only endpoint are tested. Live production scheduler starts only when `ENVIRONMENT=production`. |
| A-FR-08 | Email and WhatsApp notification system | `services/notifications.py`, `email.py`, `whatsapp.py`; event-safe templates | notifications inbox | `notifications` | `tests/test_notifications.py` | `DEPLOYMENT_GUIDE.md`, `USER_GUIDE.md` | Implemented but not fully verified | Submission/assignment/public-reply/escalation/resolution rows and safe-template behavior are tested with fake providers. Live SMTP/Meta delivery is blocked until real credentials are configured. |
| A-FR-09 | HOD escalation and override capability | HOD status/priority/escalation/assignment within department | HOD workflow pages | audit/override flags | `tests/test_tickets.py`, `tests/test_analytics.py` | `ARCHITECTURE.md` | Complete and verified | Manual HOD override and auto-route audit are covered. |
| A-FR-10 | Admin analytics dashboard with charts and reports | `analytics/overview`, `reports/tickets.pdf`, `reports/tickets.xlsx` | `analytics` page with Recharts pie/bar/line charts and downloads | none | `tests/test_analytics.py`, `tests/test_reports.py` | `API_DOCUMENTATION.md`, `USER_GUIDE.md` | Complete and verified | Aggregates are role-scoped; PDF/XLSX magic bytes, headers, filters, and role scoping are tested. |
| A-FR-11 | Broadcast announcement to students | `announcements` CRUD with audience visibility | `announcements` page | `announcements` | `tests/test_announcements.py` | `USER_GUIDE.md` | Complete and verified | Admin-only mutations, deactivation, publish timestamps, and role/department visibility are tested. |
| A-FR-12 | Export query reports to PDF and Excel | `reportlab` and `openpyxl` exporters | BFF streaming download route | none | `tests/test_reports.py` | `API_DOCUMENTATION.md` | Complete and verified | `tests/test_reports.py` checks file signatures, headers, row counts, filters, and authentication. |
| A-FR-13 | Instructor leave and auto-reply mode | `leave` CRUD, active-window auto-reply, routing exclusion | `leave` page | `instructor_leaves` | `tests/test_leave.py` | `USER_GUIDE.md` | Implemented but not fully verified | Permissions, invalid-window rejection, interval-only activation, and deactivation audit are tested. Tests do not exercise routing exclusion, so that claim is not fully verified. |
| A-FR-14 | Query history and audit log for all system activity | ticket history, status/assignment history, central audit service, admin audit API | `audit` page | audit + history tables | `tests/test_audit.py`, `tests/test_tickets.py`, `tests/test_knowledge.py` | `ARCHITECTURE.md`, `API_DOCUMENTATION.md` | Implemented but not fully verified | Ticket/AI/knowledge/announcement/leave/notification actions are audited and admin-readable. See A-FR-14b for the remaining session-event gap. |
| A-FR-14b | Authentication session events in the audit log | Google login is audited; email login/register are not | n/a | none | `tests/test_oauth.py` covers Google audit; no email-login audit test | — | Pending | Explicit audit sub-item: successful password login/registration is not written to `audit_logs`. This is a deliberate test-stability boundary in the current implementation and is disclosed rather than claimed. |
| A-IMP-01 | Unified intake from students, instructors, and departments | role-scoped tickets + three channels | role pages and web form | existing roles + `channel` | `tests/test_integrations.py`, `tests/test_tickets.py` | `USER_GUIDE.md` | Implemented but not fully verified | Code and offline tests cover all channels; live provider intake is credential-dependent. |
| A-IMP-02 | Reduce manual reading/sorting/replying | AI classification/routing/drafting | AI panel/workflow | existing | existing AI tests | `PROJECT_OVERVIEW.md` | Complete and verified | Core automation implemented and tested. |
| A-IMP-03 | Students should not need to know which department to contact | `auto_route` ticket option and inbound auto-route | create form auto-route control | `auto_routed` | `tests/test_tickets.py`, `tests/test_integrations.py` | `USER_GUIDE.md` | Complete and verified | Students may omit `department_id` and use deterministic routing. |
| A-IMP-04 | Zero-cost/free-tier tooling constraint | OpenAI BYOK; no production global fallback | settings key entry | `user_api_keys` | `tests/test_byok.py` | `README.md`, `AGENT_EVALUATION.md` | Blocked | Specific blocker: the approved derived proposal replaced Gemini/Claude/n8n/Baileys/Sheets with OpenAI/FastAPI/local DB. BYOK shifts cost to the user but cannot truthfully make the project free. |
| A-TOOL-01 | Original stack: FastAPI, React, Tailwind, LangChain, SQLAlchemy, Pydantic, PostgreSQL | implemented; LangGraph is used inside the LangChain ecosystem | Next.js 15/React 19 + Tailwind | existing | baseline + final suites | `README.md` | Complete and verified | Substitution documented. |
| A-TOOL-02 | Original visualization: Recharts or Chart.js | supplied by analytics aggregations | `recharts` pie/bar/line charts | none | `npm run typecheck`, `npm run lint`, `npm run build` | `USER_GUIDE.md` | Complete and verified | Frontend build passed with Recharts installed. |
| A-TOOL-03 | Original AI: Gemini + Claude free tier | OpenAI SDK/BYOK | OpenAI key UI | n/a | `tests/test_ai_agents.py`, `tests/test_ai_api.py` | derived proposal PDF, `README.md` | Blocked | Specific blocker: the approved derived proposal explicitly selected OpenAI. Changing providers is a new architectural decision, not a Phase 7 fix. |
| A-TOOL-04 | Original automation: n8n, Gmail API, Google Sheets logging | FastAPI services, SMTP, local PostgreSQL, audit/notification tables | no n8n/Sheets UI | local tables | `tests/test_notifications.py`, `tests/test_escalation.py` | `ARCHITECTURE.md`, `DEPLOYMENT_GUIDE.md` | Blocked | Specific blocker: derived proposal replaced these tools. Equivalent local automation is implemented and the deviation is documented. |
| A-TOOL-05 | Original WhatsApp bot: Baileys (JS) | provider-independent Meta Cloud API inbound adapter + outbound sender | n/a | `tickets.channel`, `notifications` | `tests/test_integrations.py`, `tests/test_notifications.py` | `DEPLOYMENT_GUIDE.md` | Implemented but not fully verified | Baileys itself is not used. Live Meta verification is blocked until real Cloud API credentials are configured. |

### A.2 Derived in-repo technical proposal

Source: `Smart_Query_Routing_Agentic_AI_Project_Proposal_Premium.pdf` (Version 1.1, November 2026). Its FR IDs differ from the original brief; all are included.

| ID | Derived requirement | Backend implementation | Frontend implementation | Database changes | Tests | Documentation | Status | Evidence / notes |
|---|---|---|---|---|---|---|---|---|
| A-DFR-01 | Authentication with backend-enforced RBAC | Argon2 + JWT + role deps | BFF cookie/CSRF + role nav | existing users | `tests/test_auth.py` | `API_DOCUMENTATION.md` | Complete and verified | Google OAuth added under A-FR-01. |
| A-DFR-02 | Web form creates ticket with unique reference | `services/tickets.py` | `CreateTicketForm` | tickets | `tests/test_tickets.py` | `API_DOCUMENTATION.md` | Complete and verified | `TKT-…` public reference. |
| A-DFR-03 | AI classification: category/intent/urgency/language/confidence | classification node | AI panel JSON | `ticket_ai_analyses` | `tests/test_ai_agents.py` | `API_DOCUMENTATION.md` | Complete and verified | — |
| A-DFR-04 | Department routing recommendation with backend validation | routing node + department lookup | AI panel recommendation | existing + `auto_routed` | `tests/test_ai_agents.py`, `tests/test_tickets.py` | `ARCHITECTURE.md` | Complete and verified | Automatic application added under A-FR-04. |
| A-DFR-05 | Grounded draft + staff approval | drafting/validation/approval service | AI panel | `ticket_ai_analyses` | `tests/test_ai_api.py` | `API_DOCUMENTATION.md` | Complete and verified | — |
| A-DFR-06 | Student tracking | status/history APIs | ticket detail/history | history tables | `tests/test_tickets.py` | `USER_GUIDE.md` | Complete and verified | Live-refresh gap recorded at A-FR-06b. |
| A-DFR-07 | SLA-configurable overdue flagging | `SLA_HOURS`, deterministic sweep | escalation controls | `escalated_at` | `tests/test_escalation.py` | `API_DOCUMENTATION.md` | Complete and verified | Default remains 24 hours. |
| A-DFR-08 | Email notifications for configured events | stdlib SMTP with STARTTLS/SSL, retries, delivery rows | notification center | `notifications` | `tests/test_notifications.py` | `DEPLOYMENT_GUIDE.md` | Implemented but not fully verified | Tested with fake SMTP; live credentials are externally blocked. |
| A-DFR-09 | Manager override with audit | HOD/admin patch + assignment | workflow panel | `audit_logs` | `tests/test_tickets.py` | `ARCHITECTURE.md` | Complete and verified | Auto-route override audited. |
| A-DFR-10 | Analytics: volume, categories, response time, backlog, exports | `analytics/overview` + report exporters | Recharts analytics page | none | `tests/test_analytics.py`, `tests/test_reports.py` | `USER_GUIDE.md` | Complete and verified | — |
| A-DFR-11 | Admin broadcasts to selected audiences | announcements CRUD | announcements page | `announcements` | `tests/test_announcements.py` | `USER_GUIDE.md` | Complete and verified | — |
| A-DFR-12 | Audit actor/time/ticket | central audit service + admin endpoint | audit page | `audit_logs` | `tests/test_audit.py` | `ARCHITECTURE.md` | Implemented but not fully verified | Audited actions are tested; password-login/registration session events remain unimplemented at A-FR-14b, so full-system audit coverage is not verified. |
| A-DFR-13 | Staff leave/availability respected by routing | `instructor_leaves` + routing exclusion | leave page | `instructor_leaves` | `tests/test_leave.py`, `tests/test_tickets.py` | `USER_GUIDE.md` | Implemented but not fully verified | Leave CRUD/auto-reply tests pass, but no test proves an on-leave instructor is excluded from routing. |
| A-DFR-14 | Permitted history review | history endpoints | ticket history | history tables | `tests/test_tickets.py` | `API_DOCUMENTATION.md` | Complete and verified | — |
| A-DAG-01 | Five-agent workflow: Intake, Routing, Research, Drafting, Follow-up/SLA | 5-node graph: classification, routing, knowledge_research, response_drafting, validation; SLA is a separate deterministic service | AI panel | `ticket_ai_analyses`, `agent_runs` | `tests/test_ai_agents.py`, `tests/test_agent_evaluation.py` | `ARCHITECTURE.md` | Implemented but not fully verified | Node names differ from the proposal; SLA follow-up is implemented outside the graph. Documented deviation, not a silent skip. |
| A-DAG-02 | Agent run metadata: model/status/confidence/tokens/tool I/O/permission outcome | `AgentRun` telemetry + analysis result | AI panel | `agent_runs` | `tests/test_ai_api.py` | `API_DOCUMENTATION.md` | Complete and verified | Model, status, duration, token counts, and permission outcome captured. |
| A-DAG-03 | Model must not execute arbitrary SQL/shell/send messages directly | read-only tools + approval boundary | approval UI | n/a | `tests/test_ai_agents.py`, `tests/test_ai_api.py` | `ARCHITECTURE.md` | Complete and verified | — |
| A-DATA-01 | `messages.attachments` and permitted file upload validation | validated multipart upload/list endpoints; bytes stored outside DB; metadata/checksum persisted | ticket detail attachment card with type/size hints and staff-only internal flag | `message_attachments` table in migration `feedf21773e1` | `tests/test_attachments.py`, `tests/test_knowledge.py` | `API_DOCUMENTATION.md`, `USER_GUIDE.md` | Complete and verified | Implemented during the final audit; internal attachments remain hidden from students and produce no notifications. |
| A-DATA-02 | `agent_runs`, `notifications`, `knowledge_documents` data model | all three services and models present | knowledge/notifications UI | tables in `feedf21773e1` | relevant tests | `ARCHITECTURE.md` | Complete and verified | — |
| A-DATA-03 | Closure requires resolution summary | `TicketUpdate` validation in ticket service | staff workflow includes summary field | `tickets.resolution_summary` | `tests/test_tickets.py::test_resolution_summary_is_required_for_resolved` | `USER_GUIDE.md` | Complete and verified | — |
| A-SEC-01 | Secrets in env/secrets manager, never Git | settings + env examples + encrypted BYOK + strict production validation | BFF server-only | no plaintext secrets in DB | `tests/test_byok.py`, `tests/test_release_hardening.py`, redacted secret scan | `README.md`, `DEPLOYMENT_GUIDE.md`, `RELEASE_READINESS.md` | Implemented but not fully verified | Ignore rules and image exclusions are verified. Two values in local `backend/.env` are treated as compromised and require operator rotation. Git is now initialized; a read-only audit of all 307 untracked files passed for secrets, PII, and artifacts, with zero staged files and `backend/.env` ignored. History/remote audit remains pending until a commit and remote exist. |
| A-SEC-02 | HTTPS, secure sessions, hashing, backend role checks | JWT/Argon/RBAC; HTTPS via deployment | HttpOnly cookie + CSRF | existing | `tests/test_auth.py`, role tests | `ARCHITECTURE.md` | Complete and verified | HTTPS is a deployment responsibility, documented. |
| A-SEC-03 | Data minimization to AI provider | deterministic redaction | n/a | n/a | `tests/test_ai_agents.py::test_ticket_text_is_redacted_before_prompting` | `ARCHITECTURE.md` | Complete and verified | Ticket text itself is still sent; documented. |
| A-SEC-04 | Retention/deletion/backup policies before real records | backup/restore commands; data-safety rules | n/a | none | docs review | `DEPLOYMENT_GUIDE.md` | Implemented but not fully verified | Backup, restore, rotation, rollback, and “never delete the volume” rules are documented and no records were deleted, but no explicit restore rehearsal was executed. |
| A-SEC-05 | Upload type/size validation outside web root/scanned | knowledge ingestion and ticket-attachment endpoints validate extension, signature, size, and content type; bytes stored outside web root | knowledge and ticket attachment UIs | `message_attachments`, attachment volume | `tests/test_knowledge.py::test_upload_size_and_type_limits_are_enforced`, `tests/test_attachments.py` | `ARCHITECTURE.md`, `DEPLOYMENT_GUIDE.md` | Implemented but not fully verified | Validation and safe storage are tested. No malware scanner is present, so the “scanned” clause is not satisfied. |
| A-SEC-06 | Idempotency + retries + delivery status for no duplicates | notification rows with attempts/status/dedupe; AI approval idempotency | notification UI | `notifications` | `tests/test_notifications.py`, `tests/test_ai_api.py` | `TEST_REPORT.md` | Complete and verified | — |
| A-SEC-07 | AI audit without secrets/excess PII | sanitized errors/redaction + sanitized audit details | n/a | n/a | `tests/test_ai_agents.py`, `tests/test_byok.py` | `ARCHITECTURE.md` | Complete and verified | — |
| A-SEC-08 | Rate limits, timeouts, max steps, budgets, manual fallback | durable per-user AI run counter plus existing timeouts/caps | AI panel error states | `agent_runs` | `tests/test_ai_api.py::test_ai_runs_are_rate_limited_per_user` | `ARCHITECTURE.md` | Complete and verified | 429 `ai_rate_limited`; manual fallback is the existing staff workflow. |
| A-QA-01 | Labelled evaluation dataset passing exit criteria | `evaluations/dataset.json`, deterministic evaluator | n/a | none | `tests/test_agent_evaluation.py` | `AGENT_EVALUATION.md` | Complete and verified | Synthetic data caveat is explicit in dataset, code, and both report formats. |
| A-QA-02 | Unit/integration/e2e/security/failure/accessibility tests | 187 tests across the final backend suite | frontend typecheck/lint/build | n/a | `pytest`, `npm run typecheck/lint/build` | `TEST_REPORT.md` | Implemented but not fully verified | Final backend result: 187 passed, 17 pre-existing LangSmith deprecation warnings. Browser-level accessibility automation is not present; responsive/a11y checks were manual in Phase 6.1 and UI build checks are final evidence here. |
| A-QA-03 | Backup restore + Docker stack on another machine | Compose + backup docs | Dockerfiles | external DB volume | Compose config, image builds, disposable container smoke | `DEPLOYMENT_GUIDE.md` | Implemented but not fully verified | Packaging and isolated startup are verified locally; deployment on a different host was not performed and no public deployment is approved. |
| A-OPS-01 | Docker Compose local with backend/frontend/database | `backend/Dockerfile`, `docker-compose.yml` | `frontend-next/Dockerfile` | external existing volume | `docker compose config`, image builds, isolated container smoke | `DEPLOYMENT_GUIDE.md` | Complete and verified | Both images built; backend/frontend health, startup migration, DB persistence, and BFF checks passed in disposable containers without touching the existing external volume. |
| A-OPS-02 | Health checks, named volumes, migration command, startup order | `/health`, `/api/v1/status/database`, Alembic entrypoint | `/api/health` BFF | existing external volume | Compose config + `alembic current/check` | `DEPLOYMENT_GUIDE.md` | Complete and verified | Migration head `feedf21773e1`; `alembic check` clean. |
| A-OPS-03 | Tagged images/registry, production secrets/TLS/monitoring/backup/rollback | `IMAGE_TAG`, env examples, deployment docs | build args for public IDs | no data changes | docs + compose config | `DEPLOYMENT_GUIDE.md` | Implemented but not fully verified | Provider-independent instructions exist. No registry push, public host, DNS, TLS certificate, or monitoring system was configured. |

### A.3 Development-added requirements (Phases 1–6.1)

| ID | Development requirement | Implementation | Verification | Status | Notes |
|---|---|---|---|---|---|
| A-P1-01 | Project structure, `/`, `/health`, `/api/v1/status`, structured errors, Pydantic settings/CORS | backend root modules | `tests/test_main.py` | Complete and verified | — |
| A-P1-02 | React+Vite+Tailwind shell with router, responsive dashboard/role placeholders | `frontend/` | Phase 1 smoke/build | Complete and verified | Preserved. |
| A-P3-01 | PostgreSQL 16 DB-only compose with health check, restart, named volume | `docker-compose.db.yml` | live container | Complete and verified | Preserved unchanged. |
| A-P3-02 | SQLAlchemy engine/session/get_db, shutdown disposal | `backend/app/db` | `test_database_config.py`, `test_database_health.py` | Complete and verified | — |
| A-P3-03 | Initial models and additive Alembic migration `44273a775ed8` | backend models/migrations | `alembic current` baseline | Complete and verified | — |
| A-P4-01 | Argon2id + JWT auth, register/login/me, forced student registration, dev-only admin CLI | backend auth | `tests/test_auth.py`, `tests/test_provision_admin.py` | Complete and verified | Google OAuth added in Phase 7. |
| A-P4-02 | Ticket workflow: create/list/detail/patch/assign/messages/history, pagination/filters, six-state lifecycle | backend tickets | `tests/test_tickets.py` | Complete and verified | — |
| A-P4-03 | Status/assignment history + audit transactionally, unique reference, 404 hiding | backend services | `tests/test_tickets.py` | Complete and verified | — |
| A-P4-04 | Internal notes hidden from students | backend + frontend | `tests/test_tickets.py`, `tests/test_notifications.py` | Complete and verified | Notification suppression re-verified in Phase 7. |
| A-P4-05 | Additive migration `47ebce833eae` | backend alembic | `alembic current/check` | Complete and verified | — |
| A-P5-01 | Standalone `frontend-next/`, preserve Vite and backend | `frontend-next/` | builds/live flows | Complete and verified | — |
| A-P5-02 | Next.js 15 App Router, React 19, TS strict, ESLint 9, MUI 7 + Tailwind v4 + Radix/Lucide/Sonner | frontend-next config | final typecheck/lint/build | Complete and verified | Recharts added in Phase 7. |
| A-P5-03 | BFF cookie (`smartquery_session`, HttpOnly/SameSite/Secure prod) + CSRF double-submit | `src/app/api/**` | live UI flows | Complete and verified | Phase 7 added Google and report BFF routes. |
| A-P5-04 | Typed API client with errors/cancellation | `src/lib` | live flows | Complete and verified | — |
| A-P5-05 | All role pages and ticket workflow screens | frontend-next routes | live UI verification | Complete and verified | Re-verified in Phase 6.1 and Phase 7. |
| A-P6-01 | Pinned LangGraph/LangChain, official OpenAI SDK, structured outputs | backend agents | `tests/test_ai_agents.py` | Complete and verified | — |
| A-P6-02 | Bounded retries/timeouts/deadline/recursion/token caps, sanitized errors | `llm_service.py`, config | `tests/test_ai_agents.py` | Complete and verified | Per-user rate limit added in Phase 7. |
| A-P6-03 | Read-only knowledge/department tools and deterministic redaction | `agents/tools` | `tests/test_ai_agents.py` | Complete and verified | Knowledge file replaced by DB-approved knowledge in Phase 7. |
| A-P6-04 | Trusted citations, abstention, unverified-ref stripping | drafting/validation | `tests/test_ai_agents.py` | Complete and verified | — |
| A-P6-05 | Four AI routes with staff-or-above RBAC and approval-only publish | `api/routes/ai.py` | `tests/test_ai_api.py` | Complete and verified | Staff real-workflow defect fixed in Phase 7. |
| A-P6-06 | Additive migration `b7d4e91c2a83` | backend alembic | `alembic current/check` | Complete and verified | — |
| A-P6-07 | Frontend AI panel with sourcing, validation, approval warning | `AiAssistPanel.tsx` | live admin flow | Complete and verified | — |
| A-P6-08 | Real OpenAI opt-in probe, no paid calls in tests | `cli/test_openai.py` | documented smoke | Complete and verified | — |
| A-P6.1-01 | Premium token-based visual system, brand navy/teal/canvas, MUI refinement | `globals.css`, `muiTheme.ts` | responsive audits | Complete and verified | Previously undocumented; recorded here. |
| A-P6.1-02 | Redesigned auth with labelled fields, password toggle, validation/a11y | auth pages/components | 6-width audit | Complete and verified | Google button added in Phase 7. |
| A-P6.1-03 | Redesigned shell, role nav, mobile drawer, Escape-to-close, honest empty states | shell components | 6-width audit + Escape test | Complete and verified | Phase 7 pages added to nav. |
| A-P6.1-04 | Real-data dashboards, common loading/empty/error/retry components | dashboards/common | live UI | Complete and verified | — |
| A-P6.1-05 | Redesigned ticket/admin/AI UI | ticket/admin components | live UI | Complete and verified | — |
| A-P6.1-06 | Original SVG favicon and metadata | `public/favicon.svg`, `layout.tsx` | live HTTP 200 | Complete and verified | — |
| A-P6.1-07 | Responsive 1920/1440/1366/768/390/360 with no overflow | all UI | DOM audits | Complete and verified | — |

## B. Phase 7 defect fixes and authorization verification

| ID | Requirement | Backend implementation | Frontend implementation | Database changes | Tests | Documentation | Status | Evidence / notes |
|---|---|---|---|---|---|---|---|---|
| P7-01 | Fix staff AI authorization 403 | `list_assignable_users()` in `services/tickets.py` now allows `staff`; routing path verified | no change | none | `test_assignable_user_lookup_is_role_scoped`, `test_assigned_staff_real_workflow_is_not_blocked_by_assignable_user_lookup` | `TEST_REPORT.md` | Complete and verified | Root cause fixed; both regression tests pass. |
| P7-02 | Student restrictions | `require_staff_or_above`, service ownership checks | student UI hides AI/workflow/internal notes | none | `tests/test_auth.py`, `tests/test_tickets.py`, `tests/test_ai_api.py` | `USER_GUIDE.md` | Complete and verified | Consolidated role matrix covered by role-scoped API tests. |
| P7-03 | Staff permissions | existing RBAC + P7-01 fix | staff UI | none | `tests/test_tickets.py`, `tests/test_ai_api.py` | `USER_GUIDE.md` | Complete and verified | Assigned staff can analyze, list assignable users, reply, and update allowed statuses. |
| P7-04 | HOD permissions | existing HOD role checks | HOD UI | none | `tests/test_tickets.py`, `tests/test_leave.py`, `tests/test_knowledge.py`, `tests/test_analytics.py` | `USER_GUIDE.md` | Complete and verified | Department-scoped visibility, approval, leave management, and analytics verified. |
| P7-05 | Admin permissions | existing admin role checks | admin UI | none | role tests across new modules | `USER_GUIDE.md` | Complete and verified | Admin-only audit/escalation/mutations verified. |
| P7-06 | Ticket ownership and visibility | `get_accessible_ticket`, 404 hiding | role-scoped pages | none | `tests/test_tickets.py` | `API_DOCUMENTATION.md` | Complete and verified | Student and cross-role visibility tests pass. |
| P7-07 | AI analysis authorization | AI routes + `agent_service` | AI panel | none | `tests/test_ai_api.py` | `TEST_REPORT.md` | Complete and verified | Real workflow (not a mock of the function under test) now passes for assigned staff. |
| P7-08 | Internal note privacy | `services/tickets.py` message filtering + notification event rules | student view hides notes | none | `tests/test_tickets.py`, `tests/test_notifications.py` | `USER_GUIDE.md` | Complete and verified | Internal notes are hidden and generate no email/WhatsApp/in-app notification. |

## C. Per-user OpenAI API keys (BYOK)

| ID | Requirement | Backend implementation | Frontend implementation | Database changes | Tests | Documentation | Status | Evidence / notes |
|---|---|---|---|---|---|---|---|---|
| C-01 | Add own OpenAI API key | `services/byok.py`, `api/routes/settings.py` | settings page posts to BFF only | `user_api_keys` | `tests/test_byok.py` | `USER_GUIDE.md`, `API_DOCUMENTATION.md` | Complete and verified | Upsert creates one encrypted row per user. |
| C-02 | Validate key | injected provider validator + `POST /settings/api-keys/validate` | status/validation UI | validation metadata | `test_validation_success_and_failure_with_injected_validator` | `API_DOCUMENTATION.md` | Complete and verified | Live validation requires a real OpenAI key; no secret is logged or returned. |
| C-03 | Replace key | encrypted upsert | settings replace action | same row updated | `test_replace_semantics_keep_one_encrypted_row` | `API_DOCUMENTATION.md` | Complete and verified | — |
| C-04 | Delete key | authenticated delete | settings delete action | row removed | `test_delete_removes_only_the_authenticated_users_key` | `API_DOCUMENTATION.md` | Complete and verified | — |
| C-05 | Configuration status without secret | status response with `has_key`, `key_hint`, timestamps | settings status card | metadata | `test_status_never_returns_secret` | `API_DOCUMENTATION.md` | Complete and verified | No key material in response. |
| C-06 | Encrypt keys at rest with deployment env var | `core/encryption.py` Fernet service | n/a | ciphertext columns | `test_encryption_roundtrip_hint_and_fail_closed` | `DEPLOYMENT_GUIDE.md` | Complete and verified | `BYOK_ENCRYPTION_KEY` required in production. |
| C-07 | Never expose key to frontend JS / browser storage | BFF/server-only flow | no localStorage/sessionStorage of key | n/a | `tests/test_byok.py`, frontend build | `ARCHITECTURE.md` | Complete and verified | Frontend shows only backend metadata and `key_hint`. |
| C-08 | Never log secrets | secret-free status and error paths | no echo of key | n/a | `test_status_never_returns_secret`, code review | `ARCHITECTURE.md` | Complete and verified | Raw key is only accepted in the request body and encrypted before persistence. |
| C-09 | User-level isolation | `user_id` scoped service queries | n/a | user FK | `test_user_cannot_read_replace_or_delete_another_users_key` | `API_DOCUMENTATION.md` | Complete and verified | — |
| C-10 | Never silently use another user's key | BYOK resolver is always called with requesting user | n/a | user FK | `test_ai_endpoint_requires_personal_key_without_fallback` | `TEST_REPORT.md` | Complete and verified | Fail closed with 402 `ai_personal_key_required`. |
| C-11 | No global admin key fallback in production | config validator + runtime environment check | n/a | n/a | config test + BYOK test | `DEPLOYMENT_GUIDE.md` | Complete and verified | `ALLOW_GLOBAL_OPENAI_FALLBACK=true` raises at settings load in production. |
| C-12 | Clear missing-personal-key UI message | 402 error contract | settings + AI panel message | n/a | `tests/test_byok.py` | `USER_GUIDE.md` | Complete and verified | Frontend build includes the settings guidance. |

## D. Agentic AI evaluation

All evaluation artifacts explicitly state that the dataset is synthetic and is **not** real university performance.

| ID | Requirement | Implementation | Tests | Documentation | Status | Evidence / notes |
|---|---|---|---|---|---|---|
| D-01 | Labelled synthetic university-query dataset | `backend/evaluations/dataset.json`, `synthetic-v1.0.0`, 24 labelled queries | `test_dataset_schema_is_valid_and_covers_required_topics` | `AGENT_EVALUATION.md` | Complete and verified | Dataset includes intent/query/priority/department/knowledge/citation expectations. |
| D-02 | Intent classification evaluation | offline evaluator intents | offline eval tests | `AGENT_EVALUATION.md` | Complete and verified | — |
| D-03 | Query classification evaluation | offline evaluator categories | offline eval tests | `AGENT_EVALUATION.md` | Complete and verified | — |
| D-04 | Priority prediction evaluation | offline evaluator priority | offline eval tests | `AGENT_EVALUATION.md` | Complete and verified | — |
| D-05 | Department routing evaluation | offline evaluator department | offline eval tests | `AGENT_EVALUATION.md` | Complete and verified | — |
| D-06 | Knowledge retrieval evaluation | offline evaluator retrieval | offline eval tests | `AGENT_EVALUATION.md` | Complete and verified | — |
| D-07 | Citation correctness | offline evaluator citation check | offline eval tests | `AGENT_EVALUATION.md` | Complete and verified | — |
| D-08 | Unsupported claim detection | offline evaluator unsupported-claim check | offline eval tests | `AGENT_EVALUATION.md` | Complete and verified | — |
| D-09 | Abstention behavior | abstention cases | `test_abstention_cases_are_handled_without_citations` | `AGENT_EVALUATION.md` | Complete and verified | — |
| D-10 | Latency measurement | per-run duration recorded | `test_metrics_are_recomputed_from_per_record_results` | `AGENT_EVALUATION.md`, `evaluation.json` | Complete and verified | Offline pipeline latency, not production SLA. |
| D-11 | Token usage/cost where available | live mode captures usage when provider supplies it | offline mode asserts no tokens/cost | `AGENT_EVALUATION.md` | Complete and verified | Offline reports show zero tokens/cost. |
| D-12 | Deterministic offline evaluation | default CLI mode | `pytest -q tests/test_agent_evaluation.py` (8 passed) | `AGENT_EVALUATION.md` | Complete and verified | No network calls in offline mode. |
| D-13 | Optional live OpenAI evaluation | explicit `--live` + key + confirmation | `test_live_mode_requires_explicit_opt_in_and_key` | `AGENT_EVALUATION.md` | Complete and verified | Opt-in guard verified; a paid live run was not performed. |
| D-14 | JSON + human-readable output | `eval_reports/evaluation.json`, `evaluation.md` | `test_offline_evaluator_writes_files_with_matching_counts` | `AGENT_EVALUATION.md` | Complete and verified | Both generated artifacts exist. |
| D-15 | Dataset/model versioning | dataset + model metadata in reports | `test_reports_include_version_metadata_and_synthetic_caveat` | `AGENT_EVALUATION.md` | Complete and verified | — |

## E. Approved knowledge management

| ID | Requirement | Backend implementation | Frontend implementation | Database changes | Tests | Documentation | Status | Evidence / notes |
|---|---|---|---|---|---|---|---|---|
| E-01 | Admin/HOD knowledge management | `api/routes/knowledge.py`, `services/knowledge.py`, manager role deps | knowledge page with role guards | `knowledge_documents` | `tests/test_knowledge.py` | `USER_GUIDE.md`, `API_DOCUMENTATION.md` | Complete and verified | Students cannot read; staff cannot manage. |
| E-02 | Document upload | multipart upload with source key/title/department | upload form | metadata + content | `test_text_upload_creates_unapproved_version_and_audit` | `API_DOCUMENTATION.md` | Complete and verified | Uploaded documents start unapproved. |
| E-03 | PDF/text ingestion | `pypdf` + UTF-8 text/markdown ingestion | file input | `content_text` | `test_pdf_upload_is_parsed_with_pypdf` | `ARCHITECTURE.md` | Complete and verified | Size/type limits tested. |
| E-04 | Approval and deactivation | manager endpoints + audit | approve/deactivate actions | status + approver fields | `test_approval_and_deactivation_are_audited` | `USER_GUIDE.md` | Complete and verified | — |
| E-05 | Version tracking | per-source-key version increments + version list endpoint | version display | unique version constraint | `test_version_increments_per_source_key_and_versions_endpoint` | `API_DOCUMENTATION.md` | Complete and verified | — |
| E-06 | Source citations | approved knowledge repository emits title/version/source key | AI panel citations | document/version IDs | `test_approved_active_document_is_retrieved_with_citation_and_scope` | `AGENT_EVALUATION.md`, `ARCHITECTURE.md` | Complete and verified | — |
| E-07 | Approved-source-only retrieval | `DatabaseKnowledgeRepository` filters `is_approved AND is_active` | n/a | status flags | `test_unapproved_document_is_never_retrieved`, `test_deactivated_document_disappears_from_repository` | `ARCHITECTURE.md` | Complete and verified | Default AI runs now use this repository. |
| E-08 | Working management interface | APIs | knowledge page upload/list/approve/deactivate/versions | none | frontend typecheck/lint/build | `USER_GUIDE.md` | Complete and verified | Production build passed; nav is role-filtered. |

## F. Email automation

| ID | Requirement | Backend implementation | Frontend implementation | Database changes | Tests | Documentation | Status | Evidence / notes |
|---|---|---|---|---|---|---|---|---|
| F-01 | SMTP ticket submission notification | ticket creation hook → notification service → email row | notification center | `notifications` | `test_new_ticket_notifies_staff_hod_and_admin_by_email_and_in_app` | `DEPLOYMENT_GUIDE.md` | Implemented but not fully verified | Fake SMTP path verified; live SMTP delivery blocked on real credentials. |
| F-02 | SMTP assignment notification | assignment hook | notification center | `notifications` | `test_assignment_auto_reply_is_public_audited_and_notifies_student` | `USER_GUIDE.md` | Implemented but not fully verified | Same live-SMTP caveat. |
| F-03 | SMTP public reply notification | public-message hook only | notification center | `notifications` | `tests/test_notifications.py` | `USER_GUIDE.md` | Implemented but not fully verified | Same live-SMTP caveat. |
| F-04 | SMTP escalation notification | escalation sweep hook | notification center | `notifications`, `tickets.escalated_at` | `test_sweep_escalates_once_audits_and_notifies_all_participants` | `USER_GUIDE.md` | Implemented but not fully verified | Same live-SMTP caveat. |
| F-05 | SMTP resolution notification | resolved/closed transition hook | notification center | `notifications` | `tests/test_notifications.py` | `USER_GUIDE.md` | Implemented but not fully verified | Same live-SMTP caveat. |
| F-06 | Internal notes never emailed | public-only event filter | n/a | event type | `test_internal_notes_create_no_notifications_and_never_reach_students` | `ARCHITECTURE.md` | Complete and verified | — |
| F-07 | Unapproved AI drafts never emailed | no notification event until human approval | n/a | none | `test_unapproved_ai_draft_is_never_emailed` | `ARCHITECTURE.md` | Complete and verified | — |
| F-08 | SMTP failure does not break ticket ops | transport failures caught and recorded | n/a | attempts/status | `test_smtp_failure_is_recorded_without_failing_ticket_mutation` | `TEST_REPORT.md` | Complete and verified | — |
| F-09 | Professional templates | subject/body templates with ticket reference and safe wording | n/a | n/a | `tests/test_notifications.py` | `USER_GUIDE.md` | Complete and verified | Templates exclude internal notes and drafts. |
| F-10 | Retry and audit behavior | configurable attempts, delivery status, audit rows | n/a | attempts/status | `test_smtp_failure_is_recorded_without_failing_ticket_mutation`, `test_email_rows_are_idempotent_within_short_window` | `TEST_REPORT.md` | Complete and verified | WhatsApp failure path also tested. |

## G. Remaining original feature implementation/verification

| ID | Requirement | Backend implementation | Frontend implementation | Database changes | Tests | Documentation | Status | Evidence / notes |
|---|---|---|---|---|---|---|---|---|
| G-01 | Google OAuth2 safe integration | real ID-token verification, account linking, no role escalation | BFF credential exchange + button | `user_oauth_accounts` | `tests/test_oauth.py` | `DEPLOYMENT_GUIDE.md` | Implemented but not fully verified | Live Google client credentials required. |
| G-02 | Multi-channel submission endpoints | email/WhatsApp inbound + web | web form | `tickets.channel` | `tests/test_integrations.py` | `API_DOCUMENTATION.md` | Implemented but not fully verified | Offline tested; live providers blocked. |
| G-03 | 24h escalation automation + notification | `SLA_HOURS`, sweep, repeat-safe audit/notifications | HOD/admin controls | `escalated_at` | `tests/test_escalation.py` | `USER_GUIDE.md` | Complete and verified | Deterministic clock tests; no live production scheduler run. |
| G-04 | HOD override regression coverage | existing | existing | none | `tests/test_tickets.py`, `tests/test_analytics.py` | `TEST_REPORT.md` | Complete and verified | — |
| G-05 | Admin analytics endpoint + UI | aggregation endpoint | Recharts page | none | `tests/test_analytics.py` | `USER_GUIDE.md` | Complete and verified | — |
| G-06 | Broadcast announcements | CRUD + audience rules | announcements page | `announcements` | `tests/test_announcements.py` | `USER_GUIDE.md` | Complete and verified | — |
| G-07 | PDF/Excel reports | PDF/XLSX endpoints | BFF stream route | none | `tests/test_reports.py` | `API_DOCUMENTATION.md` | Complete and verified | — |
| G-08 | Instructor leave/auto-reply | CRUD + active-window checks | leave page | `instructor_leaves` | `tests/test_leave.py` | `USER_GUIDE.md` | Complete and verified | — |
| G-09 | WhatsApp integration | Meta Cloud API adapter + inbound webhook | notification center | `notifications`, `tickets.channel` | `tests/test_integrations.py`, `tests/test_notifications.py` | `DEPLOYMENT_GUIDE.md` | Implemented but not fully verified | Live Meta access token/phone number ID required. |
| G-10 | Query history/audit verification | existing + admin audit API | ticket history + audit page | history/audit tables | `tests/test_audit.py`, `tests/test_tickets.py` | `USER_GUIDE.md` | Complete and verified | Session-event gap disclosed at A-FR-14b. |

## H. Production Docker

| ID | Requirement | Implementation | Verification | Documentation | Status | Evidence / notes |
|---|---|---|---|---|---|---|
| H-01 | Backend Dockerfile | non-root `python:3.11-slim`, Alembic entrypoint, health check | final `docker build -t smartquery-backend:phase7 ./backend` succeeded | `DEPLOYMENT_GUIDE.md` | Complete and verified | Rebuilt after the attachment/webhook source changes. |
| H-02 | Next.js frontend Dockerfile | multi-stage `node:20-alpine`, non-root runtime, health check, runtime TypeScript for `next.config.ts` | final `docker build` succeeded and container smoke passed | `DEPLOYMENT_GUIDE.md` | Complete and verified | Container smoke found and fixed a missing-runtime-TypeScript defect before final verification. |
| H-03 | Production Docker Compose | backend/frontend/postgres, external existing volume, no host DB/backend ports | `docker compose config --quiet` passed for both compose files | `DEPLOYMENT_GUIDE.md` | Complete and verified | `docker-compose.db.yml` remains byte-preserved. |
| H-04 | Health checks | backend `/health`, frontend `/api/health`, postgres `pg_isready` | scratch container smoke: all healthy/ready | `DEPLOYMENT_GUIDE.md` | Complete and verified | BFF `/api/auth/session` and unauthenticated 401 behavior were also checked. |
| H-05 | Persistent PostgreSQL | external volume `smartquerysystem_smartquery_postgres_data` | `docker compose config`, local DB queries | `DEPLOYMENT_GUIDE.md` | Complete and verified | Never delete or recreate the volume. |
| H-06 | Internal service networking | named bridge `smartquerysystem_internal` | `docker compose config` | `ARCHITECTURE.md` | Complete and verified | Only frontend port is published. |
| H-07 | Non-root app execution | UID/GID 10001 in both Dockerfiles | Dockerfile inspection | `DEPLOYMENT_GUIDE.md` | Complete and verified | Both images declare non-root users. |
| H-08 | Safe startup + migration | idempotent `alembic upgrade head` entrypoint, opt-out flag | `alembic current` = `feedf21773e1`, `alembic check` clean | `DEPLOYMENT_GUIDE.md` | Complete and verified | — |
| H-09 | Environment examples | root and backend `.env.example` files | file review + Compose interpolation | `DEPLOYMENT_GUIDE.md` | Complete and verified | Placeholders only. |
| H-10 | Backup/restore instructions | `pg_dump`/`pg_restore`, secret rotation, rollback, attachment-volume snapshots | docs review | `DEPLOYMENT_GUIDE.md` | Complete and verified | No destructive restore was executed. |
| H-11 | Persistent ticket attachment storage | `ATTACHMENT_STORAGE_DIR` and named volume `smartquerysystem_smartquery_attachments_data` | Compose config + scratch container mount | `DEPLOYMENT_GUIDE.md` | Complete and verified | Metadata/checksums are in PostgreSQL; bytes are outside the web root. |

## I. Deployment preparation

| ID | Requirement | Documentation | Status | Evidence / notes |
|---|---|---|---|---|
| I-01 | Production environment variables | `DEPLOYMENT_GUIDE.md`, `.env.example` | Complete and verified | All Phase 7 settings documented. |
| I-02 | Domain and HTTPS | `DEPLOYMENT_GUIDE.md` | Implemented but not fully verified | Provider-independent reverse-proxy guidance exists; no domain, DNS, or TLS certificate was configured or verified. |
| I-03 | Database connection | `DEPLOYMENT_GUIDE.md` | Implemented but not fully verified | Internal `postgres` hostname and external volume are documented; no managed database or public deployment connection was exercised. |
| I-04 | Docker image build commands | `DEPLOYMENT_GUIDE.md` | Complete and verified | Commands documented. |
| I-05 | Deployment commands | `DEPLOYMENT_GUIDE.md` | Implemented but not fully verified | No public deployment or approval. |
| I-06 | Migration procedure | `DEPLOYMENT_GUIDE.md` | Implemented but not fully verified | Startup migration and one-off opt-out are documented and locally exercised; no production migration was performed. |
| I-07 | Health checks | `DEPLOYMENT_GUIDE.md` | Implemented but not fully verified | Checks exist and passed in disposable containers; no public deployment was monitored. |
| I-08 | Backup/recovery | `DEPLOYMENT_GUIDE.md` | Implemented but not fully verified | Commands and warnings are documented; no explicit restore rehearsal was executed. |
| I-09 | Rollback | `DEPLOYMENT_GUIDE.md` | Implemented but not fully verified | Tag-change procedure and migration warning are documented; no production rollback was exercised. |

## J. Complete testing

Final command output and counts are in `docs/TEST_REPORT.md`.

| ID | Check | Command / method | Status | Evidence / notes |
|---|---|---|---|---|
| J-01 | Backend pytest | `python -m pytest -q` | Complete and verified | 187 passed, 17 pre-existing warnings in 294.79s. |
| J-02 | Backend compile | `python -m compileall -q app tests evaluations` | Complete and verified | Clean. |
| J-03 | Migration check | `alembic current`, `alembic check` | Complete and verified | Head `feedf21773e1`; check clean. |
| J-04 | Frontend typecheck | `npm run typecheck` | Complete and verified | Passed after all Phase 7 UI changes. |
| J-05 | Frontend lint | `npm run lint` | Complete and verified | Passed after all Phase 7 UI changes. |
| J-06 | Frontend production build | `npm run build` | Complete and verified | Passed; 13/13 static pages generated. |
| J-07 | Backend Docker image build | `docker build -t smartquery-backend:phase7 ./backend` | Complete and verified | Final source rebuild exited 0 and tagged `smartquery-backend:phase7`. |
| J-08 | Frontend Docker image build | `docker build -t smartquery-frontend:phase7 ./frontend-next` | Complete and verified | First smoke found a packaging defect; corrected image rebuilt and passed container smoke. |
| J-09 | Compose validation | `docker compose -f docker-compose.yml config --quiet` | Complete and verified | Passed for both compose files. |
| J-10 | Container health | isolated container smoke + health checks | Complete and verified | Backend, frontend, and PostgreSQL checks passed in disposable containers; scratch resources removed. |
| J-11 | Database persistence | scratch PostgreSQL restart, verify Alembic row | Complete and verified | `feedf21773e1` persisted across scratch container restart; existing external volume untouched. |
| J-12 | E2E registration/login/logout/4 roles | API-level role tests + Phase 6.1 browser audit | Complete and verified | Backend role matrix passes; browser audit previously passed. |
| J-13 | E2E ticket workflows | API-level workflow tests + Phase 6.1 browser audit | Complete and verified | Creation, assignment, replies, history, internal notes, escalation. |
| J-14 | E2E AI analysis/draft approval | API-level real-workflow tests | Complete and verified | Staff 403 defect fixed; approval validation and idempotency tested. |
| J-15 | E2E BYOK isolation | API tests | Complete and verified | Isolation, fail-closed, replacement, deletion, status secrecy. |
| J-16 | E2E knowledge approval | API + frontend build | Complete and verified | Upload→approve→retrieve→deactivate tested; UI build verified. |
| J-17 | E2E email notifications | fake SMTP tests; live SMTP blocked | Complete and verified for offline path | Live delivery blocked on real SMTP credentials. |
| J-18 | E2E escalation | deterministic clock tests | Complete and verified | Repeat-safe sweep and admin-only endpoint tested. |
| J-19 | E2E reports | endpoint tests | Complete and verified | PDF/XLSX signatures, headers, filters, role scoping. |

## K. Final documentation deliverables

| ID | File | Status | Notes |
|---|---|---|---|
| K-01 | `docs/MASTER_REQUIREMENTS_CHECKLIST.md` | Complete and verified | This file; all requirements mapped with explicit statuses, including Section M audit reconciliation. Final decision is in `docs/RELEASE_READINESS.md`. |
| K-02 | `docs/AGENT_EVALUATION.md` | Complete and verified | Synthetic caveat, files, metrics, CLI, versioning. |
| K-03 | `docs/DEPLOYMENT_GUIDE.md` | Complete and verified | Provider-independent packaging and operations. |
| K-04 | `docs/USER_GUIDE.md` | Complete and verified | Role-based usage and provider caveats. |
| K-05 | `docs/TEST_REPORT.md` | Complete and verified | Final evidence consolidation with exact commands/results and blocked checks. |
| K-06 | `docs/ARCHITECTURE.md` | Complete and verified | Phase 7 architecture reviewed and reconciled with 41 OpenAPI paths and attachment/webhook implementation. |
| K-07 | `docs/API_DOCUMENTATION.md` | Complete and verified | Phase 7 endpoint reference reviewed and updated with attachment and WhatsApp handshake routes. |
| K-08 | `docs/DEVELOPMENT_ROADMAP.md` | Complete and verified | Phase 7 status reconciled with final 187-test and 41-path evidence. |
| K-09 | `README.md` | Complete and verified | Phase 7 overview, startup, caveats, and report links reconciled with final evidence. |

## L. Summary of explicit non-completions and blockers

| ID | Item | Category | Reason / next action |
|---|---|---|---|
| L-01 | Instructor-level automatic routing | Pending | Department auto-route is implemented; direct instructor selection remains manual. Needs product decision before adding model-driven assignment. |
| L-02 | Live status polling/SSE | Pending | On-demand tracking works; automatic refresh was not implemented. Add polling or SSE if “real-time” is interpreted strictly. |
| L-03 | Password-login/registration audit events | Pending | Google login is audited; email session events are not. Add cautiously because test helpers log in on every request. |
| L-04 | Google OAuth live verification | Blocked | Requires real Google Cloud OAuth client ID and configured JavaScript origin. |
| L-05 | SMTP live verification | Blocked | Requires real SMTP host, mailbox, app password, and verified `MAIL_FROM` domain. |
| L-06 | WhatsApp live verification | Blocked | Requires real Meta WhatsApp Cloud API token, phone number ID, and webhook token. |
| L-07 | OpenAI live evaluation/live key validation | Blocked | Requires an explicitly configured user personal key; no production global fallback. |
| L-08 | Zero-cost/Gemini+Claude/n8n/Baileys/Sheets tool chain | Blocked | Conflicts with the approved derived proposal and implemented OpenAI/FastAPI/local DB architecture. |
| L-09 | Public deployment | Blocked | No approval; provider-independent packaging only. |

## M. Final release-readiness audit reconciliation

This section records every finding and remediation from the final pre-deployment audit. Status values follow the same vocabulary as Section A. No secret value is reproduced; findings are identified by path, line, variable, and pattern only.

| ID | Finding / correction | Disposition | Evidence and remaining operator action |
| --- | --- | --- | --- |
| M-01 | No `.git` repository existed during the original audit | Implemented but not fully verified | Git is now initialized (`git rev-parse --is-inside-work-tree=true`). A read-only audit of all 307 untracked files passed for secrets, credentials, PII, and artifacts; zero files are staged and `backend/.env` is ignored. No commit, remote, or push exists, so history/remote audit remains pending. Nothing was staged or pushed by this audit. |
| M-02 | `backend/.env:42` contains a likely live OpenAI key pattern under `OPENAI_API_KEY` | Blocked — operator action | Compromised by audit policy. Revoke/rotate at OpenAI, store the replacement only in a secret manager, and verify the old key is disabled. It was not printed, copied, modified, or claimed as rotated. |
| M-03 | `backend/.env:51` contains a valid Fernet-key shape under `BYOK_ENCRYPTION_KEY` | Blocked — operator action | Treat as compromised. Follow `DEPLOYMENT_GUIDE.md` §11.1: dry-run, commit re-encryption, verify, then update the secret manager and restart. Do not replace the configured value before the commit succeeds. |
| M-04 | Root `.gitignore` lacked runtime/report/temp/key rules | Complete and verified | Added `backend/var/`, `backend/eval_reports/`, `*.log`, `*.db`, `*.sqlite*`, `*.pem`, `*.key`, `*.p12`, `*.pfx`, backup/temp/swap patterns, caches, and build artifacts while preserving `.env.example`. Verified by `tests/test_release_hardening.py`. |
| M-05 | Strict production validation accepted placeholder/default secrets and unsafe config | Complete and verified | `config.py` now rejects `DEBUG=true`, global fallback, non-HS256 JWT, placeholder/known-dev or weak JWT secrets, missing/invalid/known-dev Fernet keys, placeholder DB credentials, localhost external DB URLs, unencrypted external DB URLs, wildcard/localhost CORS, and placeholder provider identities. Local development remains functional. |
| M-06 | BYOK keys could not be rotated safely | Complete and verified | Added `app/cli/rotate_byok_encryption_key.py` with env-only keys, dry-run, all-row pre-decryption, single-transaction re-encryption, post-commit verification, rollback on failure, and no key output. Covered by `tests/test_byok_rotation.py`. |
| M-07 | Raw provider exception text could be stored in `Notification.last_error` and exposed by the debug handler | Complete and verified | `safe_exception_summary()` retains only the exception class and context. Updated email, WhatsApp, and unhandled-error paths; regression tests assert fake secret markers and raw provider text are absent. |
| M-08 | BYOK plaintext limit could exceed the 512-character ciphertext column | Complete and verified | Maximum plaintext reduced to 256 in schema and service; `test_maximum_key_length_fits_encrypted_column` proves the Fernet token fits. |
| M-09 | Backend build context included host `__pycache__`/`.pyc` files | Complete and verified | Recursive `**/__pycache__/` and `**/*.py[cod]` rules added to `backend/.dockerignore`. Rebuild context fell from 93.72 kB to 5.82 kB; rebuilt image contains no `.pyc` files. |
| M-10 | Docker images needed secret-content verification | Complete and verified | Both `release-audit` images contain no `.env*`, keys/certs, DB files, logs, backups, temp files, generated reports, or secret-pattern matches. Runtime users are `app` and `nextjs`. |
| M-11 | Test/build counts were stale | Complete and verified | Final backend suite is 187 passed, 17 warnings in 294.79s; frontend typecheck/lint/build pass with 13/13 static pages; both Compose files validate; Compose v5.6.1 confirmed. |
| M-12 | Documentation had stale/incorrect claims | Complete and verified | `PROJECT_OVERVIEW.md` updated from Phases 1–5 to 1–7; `DEPLOYMENT_GUIDE.md` now documents the implemented WhatsApp GET handshake and expanded validation; `TEST_REPORT.md`, `README.md`, and this checklist were reconciled. |
| M-13 | Several checklist rows were overstated | Complete and verified | A-FR-13, A-DFR-12, A-DFR-13, A-SEC-01, A-SEC-04, A-SEC-05, A-QA-02, I-02, I-03, I-06–I-09 were corrected above. All nine Section L rows remain disclosed. |
| M-14 | Production/public deployment decision | Blocked | Overall release decision is **FAIL** until M-02, M-03, M-01, live provider checks, and scope deviations are resolved by the operator. Local/offline demo remains conditional PASS with documented caveats. |
