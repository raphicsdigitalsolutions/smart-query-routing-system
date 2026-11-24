# Hackathon Deployment Presentation — Smart Query Routing System

> **Current verified release status (2026-11-24):** Technical release artifacts are published and verified; formal institutional/governance approval and live provider verification remain open. Authoritative evidence: `docs/evidence/phase5_live_verification_2026-11-24.json`. Current verdict: **TECHNICAL RELEASE COMPLETE; FORMAL APPROVAL PENDING**. Historical slide values below are corrected in the 2026-11-24 addendum at the end.

## Slide 1 — Title
Smart Query Routing System  
Hackathon deployment execution — 22 Nov 2026; local reconciliation 23 Nov 2026  
Backend → DB → Frontend → Auth → Images → Documentation  
**Live demo:** https://smart-query-routing-system.netlify.app  
Status: **Technical release complete; formal approval pending**  
No secret values, tokens, or connection strings appear in this deck.

## Slide 2 — Live topology
- Frontend/BFF: Netlify Free — `https://smart-query-routing-system.netlify.app`
- Netlify deploy ID `6b02db1360e3188d7f1074c6` is **historical/unconfirmed**: authenticated deploy state and source sync NOT VERIFIED (API 401); live HTML uses Turbopack chunks while current main builds with webpack
- Backend: Vercel Hobby — `https://smart-query-backend.vercel.app`
- Deploy: `dpl_CRo9kXq4CBL8p8oSaaAyKdSjNVoM` — READY, production, source CLI; aliases `smart-query-backend.vercel.app` and `smart-query-backend-inforaphicsdigital-8444.vercel.app`
- Database: Neon `release-v1` — 17 public tables, 4 departments, 0 users, 0 tickets — `feedf21773e1` (read-only verified; no writes)
- Docker Hub: `raphicsdigitalsolutions/smart-query-system:latest` / `:v1.0.0` digest `sha256:2cf0a5dea54dffd643abf29a1fa7b72966899ff7235350b95fe1da793c9c2177`, anonymous pull verified; GHCR push still BLOCKED by missing `write:packages`

## Slide 3 — What was verified
- Backend final full suite: **229 passed, 17 warnings in 410.30s (0:06:50)**, 0 failed/errors — pre-existing LangSmith deprecations
- Frontend: typecheck/lint pass; build PASS with Next.js 16.4.6 webpack, 12/12 routes; Vitest 3 passed
- Backend root, `/health`, `/docs`, `/openapi.json`: **200** (live re-check: `/health`, `/api/v1/status`, `/api/v1/status/database` HTTP 200; `/api/v1/departments` HTTP 401 expected)
- `/api/v1/status/database`: **200 connected**; frontend root and `/api/health`: **200** (public smoke only; source sync NOT VERIFIED)
- Playwright + axe: build passed, **12 passed (2.0m)**; no serious/critical axe violations on login, student workspace, ticket detail (LOCAL VERIFIED)
- `release-v1` Neon schema read-only verified at expected Alembic head: 17 public tables, 4 departments, 0 users, 0 tickets; no writes

## Slide 4 — BFF integration smoke
- Registration/login through BFF: **200**
- Session cookie: **HttpOnly**; CSRF returned; wrong/missing CSRF: **403**
- Multipart proxy: **201**; cleanup: **200**
- PDF report: **200**, `application/pdf`, `no-store`, `%PDF-1.3`
- Temporary user and uploaded document removed; final user count 1
- Live hosted checks were deployment-time evidence, not repeated by the local reconciliation

## Slide 5 — Serverless deviations
- Background escalation worker disabled on Vercel
- `backend/vercel.json` configures one daily secret-protected sweep trigger (`0 0 * * *`); the live cron list confirms the schedule, but hosted invocation is **NOT VERIFIED**
- Attachments use `/tmp`; ephemeral and not shared
- Upload cap 4 MiB to match Vercel body limit; DB pool 1 + 0 overflow
- Migrations off; Neon already at head
- These are live facts, not future intentions

## Slide 6 — Cost and BYOK discipline
- No paid plan, upgrade, payment method, auto recharge, billing change, or billable add-on
- Vercel account confirmed Hobby; card/balance untouched
- Render refused `$0` deployment; no Render service created
- `ALLOW_GLOBAL_OPENAI_FALLBACK=false`; `OPENAI_API_KEY=` empty
- No personal OpenAI key in hosted env; production token lifetime 60 min (test-only 1440)

## Slide 7 — Brief coverage
- 14 functional requirements mapped
- Department routing, analytics, reports, announcements, audit, leave, escalation: implemented/tested
- FR-04b/FR-13: deterministic staff-only instructor routing, active leave excluded, HOD/admin never auto-assigned, no approval workflow — LOCAL VERIFIED
- FR-06: ETag/304 conditional polling + `useTicketStatusPolling`; **not SSE/push** — LOCAL VERIFIED
- FR-14: password register/login success/failure audits without secrets — LOCAL VERIFIED
- Live provider checks BLOCKED: Google OAuth, SMTP, WhatsApp, user OpenAI key
- Tool/model/hosting substitutions and zero-cost interpretation still need university approval

## Slide 8 — Container images
- Backend image built: `ghcr.io/raphicsdigitalsolutions/smart-query-backend:latest`
- Short commit tag also built: `:6f388d0`
- Frontend built locally after an npm `ETIMEDOUT` retry; `:latest` and `:6f388d0` tagged
- Remote manifests missing; push denied without `write:packages`
- Registry content, including `ghcr.io/raphicsdigitalsolutions/smart-query-system:latest`, left untouched
- No push, tag overwrite, visibility change, or deletion performed

## Slide 9 — Open gates
- GHCR publication BLOCKED; Docker Hub image published and anonymously pull-verified
- Technical release artifacts complete and verified; formal governance approval still pending
- University approval required for scope deviations, substitutions, zero-cost, leave workflow, public release
- Hosted cron schedule verified; actual invocation NOT VERIFIED
- npm audit and npm audit --omit=dev: 0 vulnerabilities after remediation
- Netlify authenticated deploy state/source sync NOT VERIFIED; owner should confirm/redeploy from GitHub main
- Secret audit triage complete; no rotation/revocation authorized or performed
- Backup/restore rehearsal PASS locally; hosted restore and malware scanner NOT VERIFIED; monitoring/retention NOT VERIFIED

## Slide 10 — Security verification
- JWT secret high entropy and differs from old compromised value; old OpenAI key revoked at deployment time
- BYOK Fernet key valid and rotated; 0 encrypted records to break
- Global key empty; fallback false; DB SSL on Neon; CORS restricted; cookies Secure + HttpOnly
- Broader secret audit: 385 tracked; 17 workspace potential; 12 git-history potential; 453 image potential; 4 local-env matches
- Audit stores field names/lengths/fingerprints only — no values printed; no rotation/revocation
- See `docs/SECRET_AUDIT_REMEDIATION_PLAN.md`

## Slide 11 — Live E2E and critical finding
- Register/login/logout, CSRF 403, roles, isolation 404: PASS (deployment-time)
- Ticket create, assign, status workflow, PDF, multipart: PASS
- Missing BYOK key gives clear 402 error; no global key used
- Fixed: 3 approved departments seeded via audited admin API; 409 on duplicate
- BLOCKED: real BYOK key add, analysis, and cross-user key test
- Cleanup: final user count 1 (admin:1); no real records touched

## Slide 12 — Department reference data fixed
- Was: 0 departments; real ticket submission returned 400
- Seeded via admin API: Registry (3), Scholarships (4), IT Services (5)
- Names sourced from repo test fixtures; no invention; DB assigned IDs
- Duplicate re-post returned 409; idempotent; 3 audit records
- Frontend: explicit select, 2 auto-routes, retrieval, assignment: PASS
- Disposable tickets/users removed; 1 admin user, 0 tickets remain

## Slide 13 — Conclusion
- Real public deployment: frontend + backend + database connected; backend at `origin/main` `2cb5595`, clean tree
- Live smoke evidence passes; local reconciliation adds deterministic routing, polling, daily cron trigger, auth audits, restore rehearsal and local malware integration
- Suitable for a live hackathon demonstration
- **TECHNICAL RELEASE COMPLETE; FORMAL APPROVAL PENDING** — not an institutionally approved production release
- Hosted cron invocation, live provider checks, Netlify source sync and GHCR publication remain BLOCKED/NOT VERIFIED
- Full evidence: `docs/HACKATHON_DEPLOYMENT_REPORT.md`, `docs/evidence/phase5_live_verification_2026-11-24.json`; slides source: `docs/HACKATHON_DEPLOYMENT_SLIDES.md`

## 2026-11-23 read-only GHCR addendum

Slide 8 records the 2026-11-22 publication state. A later read-only check
(`docs/evidence/ghcr_readonly_investigation.json`) shows that
`ghcr.io/raphicsdigitalsolutions/smart-query-system:latest` **does** exist and is anonymously pullable
at digest `sha256:417e017081a460adfe310236e13b3e117cb972c11c5c93370968aa866a2b0f0f`, matching the
recorded and local digests. The "remote manifests missing" wording is therefore superseded for that
package. No push or registry write was performed, and publication of current local changes still
requires `write:packages`. The generated PDF retains the historical 2026-11-22 slide wording; that
addendum is superseded by the 2026-11-24 addendum below.

## 2026-11-24 final verification addendum (current)

Authoritative evidence: `docs/evidence/phase5_live_verification_2026-11-24.json`.

- Git release-evidence commit: `2cb5595ee7a38c85c63223079dc9d17a290ed089` (`b51dd31` → `7ad663e` → `eb30f92` → `2cb5595`); clean working tree after that commit.
- Vercel deployment `dpl_CRo9kXq4CBL8p8oSaaAyKdSjNVoM` is READY/production/source CLI with the two aliases above. Deployed metadata commit `b51dd31` had a dirty CLI working tree, but the deployed config already contains the final daily cron and current main matches. Live cron list: one job, `0 0 * * *`, `/api/v1/tickets/escalation/sweep`; invocation NOT VERIFIED.
- Netlify public root and `/api/health` HTTP 200, but authenticated deploy state and source sync NOT VERIFIED (API 401, no token); live Turbopack chunks vs current webpack build prevent a "matches main" claim. Deploy `6b02db1360e3188d7f1074c6` is unconfirmed. Owner: confirm/redeploy from GitHub main; no redeploy performed.
- `release-v1` database read-only: `neondb`, URL fingerprint `5d1fc726d19b`, host fingerprint `141f6064ec7f`, Alembic `feedf21773e1`, 17 public tables, 4 departments, 0 users, 0 tickets, no writes. Branch identity from the git-ignored `backend/.env.release_v1` file name; hosted equality and old DB state NOT VERIFIED.
- Docker Hub `raphicsdigitalsolutions/smart-query-system:latest` / `:v1.0.0` digest `sha256:2cf0a5dea54dffd643abf29a1fa7b72966899ff7235350b95fe1da793c9c2177` (replaces stale `sha256:e9ed708…`): anonymous pull exit 0 with empty Docker config, manifest HTTP 200; container smoke healthy, UID 10001, Supervisor backend+frontend RUNNING, 4 HTTP checks 200 with disposable SQLite/no external integrations, no `.env` or key files in image.
- Final verdict: **TECHNICAL RELEASE COMPLETE; FORMAL APPROVAL PENDING**. NOT VERIFIED: Google OAuth, SMTP, Meta WhatsApp, real-user BYOK, hosted cron invocation, university approval, hosted restore/malware scanner, monitoring/retention.
