# Hackathon Deployment Presentation — Smart Query Routing System

## Slide 1 — Title
Smart Query Routing System  
Hackathon deployment execution — 22 Nov 2026; local reconciliation 23 Nov 2026  
Backend → DB → Frontend → Auth → Images → Documentation  
**Live demo:** https://smart-query-routing-system.netlify.app  
Status: **Live demonstration; formal production sign-off still open (FAIL verdict unchanged)**  
No secret values, tokens, or connection strings appear in this deck.

## Slide 2 — Live topology
- Frontend/BFF: Netlify Free — `https://smart-query-routing-system.netlify.app`
- Deploy: `6b02db1360e3188d7f1074c6` — Live
- Backend: Vercel Hobby — `https://smart-query-backend.vercel.app`
- Deploy: `dpl_3va9eirAAZ6wajnAVd2bL3kP2EVV` — Ready
- Database: Neon PostgreSQL — 17 tables — `feedf21773e1`
- GHCR: images built locally; remote push BLOCKED by missing `write:packages`; registry content untouched

## Slide 3 — What was verified
- Backend final full suite: **225 passed, 17 warnings in 265.61s (0:04:25)** — pre-existing LangSmith deprecations
- Frontend: typecheck/lint/build pass; 13/13 routes
- Backend root, `/health`, `/docs`, `/openapi.json`: **200**
- `/api/v1/status/database`: **200 connected**; frontend root and `/api/health`: **200**
- Playwright + axe: build passed, **11 passed (~1.3m)**; no serious/critical axe violations on login, student workspace, ticket detail (LOCAL VERIFIED)
- Neon schema verified at expected Alembic head

## Slide 4 — BFF integration smoke
- Registration/login through BFF: **200**
- Session cookie: **HttpOnly**; CSRF returned; wrong/missing CSRF: **403**
- Multipart proxy: **201**; cleanup: **200**
- PDF report: **200**, `application/pdf`, `no-store`, `%PDF-1.3`
- Temporary user and uploaded document removed; final user count 1
- Live hosted checks were deployment-time evidence, not repeated by the local reconciliation

## Slide 5 — Serverless deviations
- Background escalation worker disabled on Vercel
- `backend/vercel.json` configures an hourly secret-protected sweep trigger; LIVE cron execution **NOT VERIFIED**
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
- GHCR publication BLOCKED; live provider verification BLOCKED
- Prior `FAIL — DO NOT DEPLOY` governance verdict unresolved
- University approval required for scope deviations, substitutions, zero-cost, leave workflow, public release
- Hosted cron execution NOT VERIFIED
- npm audit after Playwright/axe install: 6 vulnerabilities (2 moderate, 2 high, 2 critical)
- Secret audit triage complete; no rotation/revocation authorized or performed
- Backup/restore rehearsal PASS locally; malware scan PASS_LOCAL_INTEGRATION_ONLY, NOT DEPLOYED

## Slide 10 — Security verification
- JWT secret high entropy and differs from old compromised value; old OpenAI key revoked at deployment time
- BYOK Fernet key valid and rotated; 0 encrypted records to break
- Global key empty; fallback false; DB SSL on Neon; CORS restricted; cookies Secure + HttpOnly
- Broader secret audit: 307 tracked; 16 workspace potential; 12 git-history potential; 453 image potential; 4 local-env matches
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
- Real public deployment: frontend + backend + database connected
- Live smoke evidence passes; local reconciliation adds deterministic routing, polling, cron trigger, auth audits, restore rehearsal and local malware integration
- Suitable for a live hackathon demonstration
- Not a formally approved production release; FAIL verdict remains
- Hosted cron, live provider checks and GHCR publication remain BLOCKED/NOT VERIFIED
- Full evidence: `docs/HACKATHON_DEPLOYMENT_REPORT.md`; slides source: `docs/HACKATHON_DEPLOYMENT_SLIDES.md`

## 2026-11-23 read-only GHCR addendum

Slide 8 records the 2026-11-22 publication state. A later read-only check
(`docs/evidence/ghcr_readonly_investigation.json`) shows that
`ghcr.io/raphicsdigitalsolutions/smart-query-system:latest` **does** exist and is anonymously pullable
at digest `sha256:417e017081a460adfe310236e13b3e117cb972c11c5c93370968aa866a2b0f0f`, matching the
recorded and local digests. The "remote manifests missing" wording is therefore superseded for that
package. No push or registry write was performed, and publication of current local changes still
requires `write:packages`. The generated PDF retains the historical 2026-11-22 slide wording; this
addendum is the current evidence.
