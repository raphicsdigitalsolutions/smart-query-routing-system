# Final Requirements Traceability Matrix

**Baseline Date:** 2026-11-24  
**Authoritative Brief:** `AllProjectsS26.pdf` (pp. 30–31)  
**Repository Matrix Sources:** [AUTHORITATIVE_COMPLETION_MATRIX.md](file:///C:/Users/user/OneDrive/Desktop/SmartQuerySystem/docs/AUTHORITATIVE_COMPLETION_MATRIX.md), [MASTER_REQUIREMENTS_CHECKLIST.md](file:///C:/Users/user/OneDrive/Desktop/SmartQuerySystem/docs/MASTER_REQUIREMENTS_CHECKLIST.md)

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
| FR-07 | 24-hour auto-escalation for unresolved queries | `services/escalation.py`, `POST /tickets/escalation/sweep`, `backend/vercel.json` | `tests/test_escalation.py`, `tests/test_escalation_serverless.py` | **PARTIAL** | Deterministic sweep & secret-protected cron endpoint **PASS** locally; live hosted cron run unverified. |
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

Combining the 14 Brief FRs + 9 Brief Constraints + 14 Derived FRs + 15 Agent/Data + 26 Security/Risk/QA + 9 Docker/Governance rows (**87 total rows**, reflecting latest 2026-11-24 verification after dependency remediation):
- **PASS:** **44**
- **PARTIAL** *(implemented & locally verified; live external/hosted provider check pending)*: **23**
- **BLOCKED** *(requires owner credential rotation, `write:packages` scope, or signed university governance/deviation approval)*: **20** *(note: `O-TOOL-05..07`, `O-COST-00`, `D-SEC-01/04`, `D-DOCK-02/04/05`, `D-SUB-00`, and related provider/cost governance items)*
- **FAIL:** **0** *(previous `D-QA-11` `npm audit` failure is now **PASS**)*
