# Hackathon Deployment Report — Smart Query Routing System

**Date:** 2026-11-22  
**Scope:** Final combined deployment execution: backend → health/DB verification → frontend → auth integration → container images → documentation. Updated 2026-11-23 with local-only reconciliation evidence for FR-04b/FR-06/FR-07/FR-13/FR-14.  
**Authoritative brief:** `C:\Users\user\Downloads\AllProjectsS26.pdf`, pages 30–31. No formal submission form or deadline appears on those pages; supervisor contact details are present. No supervisor contact was made.

> **Current verified release status (2026-11-24):** Technical release artifacts are published and verified; formal institutional/governance approval and live provider verification remain open. Authoritative evidence: `docs/evidence/phase5_live_verification_2026-11-24.json`. Current verdict: **TECHNICAL RELEASE COMPLETE; FORMAL APPROVAL PENDING**. The 2026-11-22 FAIL wording below is historical; the final reconciled state is in §17.
>
> This report records what was actually executed and verified. At the time of writing it did **not** revoke the earlier `FAIL — DO NOT DEPLOY` production/public governance verdict (historical). The deployment is real and reachable, but formal scope/security sign-off remains unresolved; the final current state is §17.
>
> **2026-11-23 reconciliation:** Later local-only work delivered deterministic staff-only instructor routing, conditional polling, a secret-protected cron sweep trigger, and password-auth audit events. Its evidence is **LOCAL VERIFIED** unless explicitly marked **BLOCKED**, **NOT DEPLOYED** or **NOT VERIFIED**. It did not change any live provider resource, hosted configuration, credential, registry content or production record. University approval is still required for scope deviations, tool/model/hosting substitutions, the zero-cost interpretation, the leave workflow and release/public governance; that 2026-11-23 FAIL verdict is historical and superseded by §17.

## 1. Executive status

| Area | Actual status |
| --- | --- |
| Backend API on Vercel | **READY** — FastAPI ASGI deployment `dpl_CRo9kXq4CBL8p8oSaaAyKdSjNVoM`, target `production`, source CLI; aliases `smart-query-backend.vercel.app` and `smart-query-backend-inforaphicsdigital-8444.vercel.app` |
| Neon PostgreSQL (`release-v1`) | **READ-ONLY VERIFIED** — database `neondb`, URL fingerprint `5d1fc726d19b`, host fingerprint `141f6064ec7f`, 17 public tables, 4 departments, 0 users, 0 tickets, Alembic `feedf21773e1`; no writes |
| Frontend/BFF on Netlify | **LIVE PUBLIC SMOKE** — root and `/api/health` return 200; authenticated deploy state and source sync **NOT VERIFIED** (no token; API 401) |
| Live BFF auth/CSRF/proxy/report checks | **PASS (deployment-time evidence)** — registration/login, HttpOnly session, CSRF 403, multipart 201, PDF 200 |
| Container images | Unified Supervisor image published on Docker Hub (`latest`, `v1.0.0`, digest `sha256:2cf0a5dea54dffd643abf29a1fa7b72966899ff7235350b95fe1da793c9c2177`); GHCR remote push still blocked by missing `write:packages` scope |
| Strict `$0` constraint | **PRESERVED** — no paid plan, upgrade, payment method, auto recharge, billing change, or billable add-on was added/changed |
| BYOK policy | **PRESERVED** — `ALLOW_GLOBAL_OPENAI_FALLBACK=false`, `OPENAI_API_KEY=` empty, no personal OpenAI key in hosted env |
| Formal release governance | **FORMAL APPROVAL PENDING** — technical release artifacts published and verified; signed deviation, live provider and institutional approval gaps remain open |
| FR-04b / FR-13 instructor routing | **LOCAL VERIFIED** — deterministic staff-only selection, active leave windows only, HOD/admin never auto-assigned, no approval workflow |
| FR-06 conditional polling | **LOCAL VERIFIED** — ETag/304 updates endpoint + frontend polling hook; not SSE/push |
| FR-07 cron sweep trigger | **SCHEDULE VERIFIED / INVOCATION NOT VERIFIED** — secret-protected sweep endpoint + daily `0 0 * * *` Vercel config; live cron list shows one daily job |
| FR-14 password auth audits | **LOCAL VERIFIED** — register/login success and failure events without passwords/secrets |
| Playwright + axe E2E | **LOCAL VERIFIED** — build passed (`12/12` pages, webpack), 12 passed (`2.0m`), Vitest 3 passed, no serious/critical axe violations on 3 screens |
| Backup/restore rehearsal | **LOCAL VERIFIED** — status `PASS` on disposable PostgreSQL; no hosted Neon restore |
| Malware scanning | **LOCAL VERIFIED (INTEGRATION ONLY)** — real ClamAV clean/EICAR checks; scanner disabled by default, NOT DEPLOYED |
| Secret audit | **TRIAGE ONLY** — redacted audit produced; no rotation or revocation authorized/performed |
| npm audit | **RESOLVED** — all 6 historical vulnerabilities remediated; `npm audit` and `npm audit --omit=dev` both report **0 vulnerabilities** |

## 2. Live deployment topology

| Layer | Provider / plan | Actual endpoint or identifier | State |
| --- | --- | --- | --- |
| Frontend + Next.js BFF | Netlify Free | `https://smart-query-routing-system.netlify.app` | Public smoke 200; authenticated deploy state and source sync **NOT VERIFIED**. Historical deploy ID `6b02db1360e3188d7f1074c6` could not be authenticated or confirmed; live HTML still uses Turbopack chunks while current main builds with webpack |
| Backend FastAPI | Vercel Hobby | `https://smart-query-backend.vercel.app` | READY, production; current deploy `dpl_CRo9kXq4CBL8p8oSaaAyKdSjNVoM`, source CLI (metadata commit `b51dd31`, dirty CLI working tree; current main `2cb5595` matches deployed config) |
| Backend unique URL | Vercel Hobby | `https://smart-query-backend-inforaphicsdigital-8444.vercel.app` | READY alias of the current deployment |
| Database | Neon PostgreSQL (`release-v1`) | Hosted connection stored only as a secret env var | Read-only verified: URL fingerprint `5d1fc726d19b`, host fingerprint `141f6064ec7f`, 17 public tables, 4 departments, 0 users, 0 tickets, revision `feedf21773e1`; no writes |
| Image registry | GHCR (historical) / Docker Hub (current) | Docker Hub `raphicsdigitalsolutions/smart-query-system:latest` / `:v1.0.0`; historical GHCR `.../smart-query-backend:*`, `.../smart-query-frontend:*` | Docker Hub image published at digest `sha256:2cf0a5dea54dffd643abf29a1fa7b72966899ff7235350b95fe1da793c9c2177`, anonymous pull verified (§17); historical local images and GHCR push blocked pending `write:packages` |

### Frontend configuration actually applied

- Netlify site: `smart-query-routing-system`, site ID `c897238f-5a28-42f0-9775-56830d2c6e01`.
- Build command: `next build`; publish directory: `.next`; `NODE_VERSION=22.23.2`; plugin: `@netlify/plugin-nextjs`.
- Unrelated `21YunBox` plugin removed. Netlify Codex/agent controls were not used for the final deploy.
- Both `API_BASE_URL` and `NEXT_PUBLIC_API_BASE_URL` were changed from `https://backend-pending.invalid/api/v1` to `https://smart-query-backend.vercel.app/api/v1` for Live app and Versions, then verified in the environment table.
- Triggered `Deploy project without cache`. The new deploy reached **Ready**, then **Live**; visitors kept seeing the previous live version until publish.

### Backend configuration actually applied

- Deployed locally from `backend/` using Vercel CLI so source and `.env` were not committed or pushed.
- Runtime: Vercel Python `python3.12`; ASGI entrypoint `backend/api/index.py` exposing `app.main:app`; `backend/vercel.json` rewrites all paths to `/api/index`.
- Environment imported from a local temp env file: 32 imported, 0 failed. Keys were verified by name only; no secret value was printed.
- Serverless overrides: `BACKGROUND_WORKER_ENABLED=false`, `ATTACHMENT_STORAGE_DIR=/tmp/smartquery-attachments`, `MAX_UPLOAD_BYTES=4194304`, `DB_POOL_SIZE=1`, `DB_MAX_OVERFLOW=0`, `RUN_MIGRATIONS=false`.
- A startup 500 caused by a malformed `BACKEND_CORS_ORIGINS` value was fixed by storing a JSON list string containing only the real Netlify origin; redeploy then passed all live checks.
- `backend/.env`, `backend/.env.local`, virtualenvs, tests, and local artifacts are excluded from the Vercel upload.
- `backend/vercel.json` now contains a daily cron entry (`0 0 * * *`) targeting
  `POST /api/v1/tickets/escalation/sweep`, which is gated by `X-Cron-Secret` /
  `ESCALATION_CRON_SECRET`. The live Vercel cron list shows exactly that one daily job, so schedule
  existence is verified; actual hosted invocation remains **NOT VERIFIED**. Hobby allows at most
  once per day, so the earlier hourly `0 * * * *` proposal is invalid and superseded.

## 3. Live verification evidence

### 3.1 Frontend and BFF

| Check | Result |
| --- | --- |
| `GET https://smart-query-routing-system.netlify.app/` | HTTP 200, HTML app shell |
| `GET https://smart-query-routing-system.netlify.app/api/health` | HTTP 200, `{"success":true,"status":"healthy"}` |
| Guest `GET /api/auth/session` | HTTP 200; `smartquery_csrf` cookie set |
| Register through BFF with temporary account | HTTP 200; `smartquery_session` HttpOnly cookie set; CSRF token returned |
| Valid session probe | HTTP 200; authenticated user present |
| Wrong CSRF header on unsafe BFF request | HTTP 403 |
| Missing CSRF header on unsafe BFF request | HTTP 403 |
| Raw multipart forwarding via `/api/backend/knowledge` | HTTP 201; response body 781 bytes |
| Cleanup of smoke knowledge document via BFF DELETE | HTTP 200 |
| `GET /api/reports/pdf` | HTTP 200; `application/pdf`; `Content-Disposition` present; `Cache-Control: no-store`; prefix `%PDF-1.3` |
| Temporary user and document cleanup | Confirmed; user count returned to 1, role counts `admin:1` |

The local `.env` admin credential material no longer matched the hosted admin user row; password login returned 401. No credential or database row was changed to hide that. Authenticated BFF checks used a short-lived token minted from the hosted JWT secret; the token and helper files were deleted after verification.

### 3.2 Backend and database

| Check | Result |
| --- | --- |
| `GET /` | HTTP 200; `{"success":true,"message":"Smart Query Routing System API is running","version":"1.0.0"}` |
| `GET /health` | HTTP 200; `{"success":true,"status":"healthy"}` |
| `GET /docs` | HTTP 200 |
| `GET /openapi.json` | HTTP 200 |
| `GET /api/v1/status/database` | HTTP 200; `{"success":true,"database":"connected"}` |
| Neon schema | 17 tables; `alembic_version` present; current revision `feedf21773e1` |
| Backend automated suite | Historical deployment-time run `187 passed, 17 warnings`; final local suite `229 passed, 17 warnings in 410.30s (0:06:50)`, 0 failed/errors — pre-existing LangSmith deprecations |
| Frontend local build | `npm run build` passed (Next.js 16.4.6 webpack); typecheck, lint, and Vitest (`3 passed`) passed; 12/12 pages/routes built |
| Playwright + axe E2E | LOCAL VERIFIED: build passed; 12 tests passed in 2.0m; no serious/critical axe violations on login, student workspace and ticket detail |

### 3.3 Provider and BYOK status

| Integration | Verified state |
| --- | --- |
| Google OAuth | Code/offline tests pass; live Google verification remains blocked without a real OAuth client ID/origin. |
| SMTP email | Code/fake-provider tests pass; live delivery remains blocked without real SMTP credentials and verified `MAIL_FROM`. |
| WhatsApp | Code/inbound adapter tests pass; live Meta verification remains blocked without real token, phone ID, and webhook token. |
| User OpenAI BYOK | Policy and encryption tests pass; live user key validation/evaluation remains blocked because no personal key was provided. No global fallback is enabled. |

## 4. Serverless deviations that are live

These are real production configuration facts, not future plans:

| Deviation | Live behavior |
| --- | --- |
| Background escalation worker | The in-process production worker is disabled on Vercel. The 24-hour deterministic sweep and admin endpoint remain implemented/tested, and `backend/vercel.json` configures a daily `0 0 * * *` secret-protected cron trigger (one job in the live cron list). Hosted invocation is **NOT VERIFIED**; do not claim an escalation has actually run. |
| Attachment bytes | Written to `/tmp/smartquery-attachments`; ephemeral and not shared across instances. A persistent object store is required for durable attachments. |
| Upload limit | `4194304` bytes (4 MiB), matching Vercel's standard request-body constraint rather than the original 5 MiB local default. |
| Database pool | `DB_POOL_SIZE=1`, `DB_MAX_OVERFLOW=0` to fit serverless connection limits. |
| Migrations | `RUN_MIGRATIONS=false`; Neon was independently verified already at head `feedf21773e1`. |
| Vercel project | Hobby plan. Existing user card/balance was not used, inspected for charging, or modified by the assistant. |
| Vercel protection | Deployment inspection listed `vercel_authentication`; all public checks above nevertheless succeeded without interactive authentication. |

## 5. Container image status

| Image | Local state | Remote state |
| --- | --- | --- |
| `ghcr.io/raphicsdigitalsolutions/smart-query-backend:latest` | Built locally, image ID `a6738e3195be`, 512 MB | `docker manifest inspect` returned `manifest unknown`; push failed with `permission_denied: The token provided does not match expected scopes` |
| `ghcr.io/raphicsdigitalsolutions/smart-query-backend:6f388d0` | Built locally, same image ID | Not yet verified remotely for the same reason |
| `ghcr.io/raphicsdigitalsolutions/smart-query-frontend:latest` | Built locally after retry, image ID `a3a491465717`, 1.64 GB; `:6f388d0` tag also created | Not pushed; push also requires the same `write:packages` credential |

The first frontend build attempt failed at `npm ci` with `ETIMEDOUT` fetching `@types/d3-scale`. The retry reused cached layers and completed successfully; the shell wrapper still reported exit code 1 from the output pipeline, so the image was verified directly with `docker image inspect` before tagging.

The existing GitHub credential has scopes `gist, repo, workflow`, but not `write:packages`. Per operator choice, the intended flow is a local PAT file at `C:\Users\user\AppData\Local\Temp\opencode\ghcr_pat.txt`, read only for `docker login`, followed by image push and secure deletion of the file. No token value is to be printed or committed.

As of 2026-11-23 publication is still **BLOCKED** and no registry content was changed, including `ghcr.io/raphicsdigitalsolutions/smart-query-system:latest`. No push, pull, tag overwrite, visibility change or deletion was performed.

## 6. Brief coverage — pages 30–31

| FR | Brief requirement | Actual status |
| --- | --- | --- |
| FR-01 | Role-based login with Google OAuth2 | Implemented/tested; live OAuth blocked |
| FR-02 | Email, web form, WhatsApp submission | Web live; provider intake code tested; live SMTP/Meta blocked |
| FR-03 | AI classification and intent detection | Implemented/tested offline; live AI requires user BYOK |
| FR-04 | Route to department or instructor | Department routing live/tested; deterministic staff-only instructor auto-routing LOCAL VERIFIED (active leave excluded; HOD/admin never auto-assigned; no approval workflow) |
| FR-05 | AI draft replies for staff | Implemented/tested; live generation requires user BYOK |
| FR-06 | Real-time student status tracking | Conditional polling LOCAL VERIFIED (ETag/304 updates endpoint + hook); not SSE/push |
| FR-07 | 24-hour auto-escalation | Sweep tested; secret-protected cron endpoint + daily repo config verified and one daily job in the live cron list; hosted invocation NOT VERIFIED; in-process worker disabled on Vercel |
| FR-08 | Email and WhatsApp notifications | In-app/DB behavior tested; live external delivery blocked |
| FR-09 | HOD escalation and override | Implemented/tested |
| FR-10 | Admin analytics dashboard | Implemented/tested |
| FR-11 | Broadcast announcements | Implemented/tested |
| FR-12 | PDF and Excel exports | Implemented/tested; PDF verified live through BFF |
| FR-13 | Instructor leave and auto-reply | CRUD/auto-reply tested; active-window routing exclusion LOCAL VERIFIED; university approval of leave workflow still open |
| FR-14 | Query history and audit log | Implemented/tested; password registration/login success/failure audit events LOCAL VERIFIED (no passwords/secrets stored) |

### Brief tool deviations still requiring acknowledged approval

- Gemini/Claude free tiers → OpenAI SDK with user BYOK.
- n8n → FastAPI services and deterministic schedulers/sweeps.
- Gmail API → SMTP adapter.
- Baileys → Meta WhatsApp Cloud API adapter.
- Google Sheets → PostgreSQL audit/notification tables.
- Supabase/Render free tiers → Neon PostgreSQL + Vercel Hobby after Render refused `$0` deployment due card verification.

## 7. Final checklist and unresolved gates

| Item | Status |
| --- | --- |
| Backend deployed and healthy | **PASS** |
| Database connected and at expected schema | **PASS** |
| Frontend deployed and healthy | **PASS** |
| BFF API env no longer points to placeholder host | **PASS** |
| Live auth, CSRF, multipart, and report checks | **PASS** |
| No paid plans, upgrades, payment methods, add-ons, or billing changes | **PASS** |
| BYOK-only policy preserved | **PASS** |
| GHCR package existence / remote publish | **PARTIAL** — existing `ghcr.io/raphicsdigitalsolutions/smart-query-system:latest` verified anonymously pullable at digest `sha256:417e017081a460adfe310236e13b3e117cb972c11c5c93370968aa866a2b0f0f`; republishing current local changes remains **BLOCKED** pending `write:packages` |
| Live Google OAuth, SMTP, WhatsApp, user OpenAI key | **BLOCKED** — real credentials not supplied |
| FR-04b instructor auto-routing | **LOCAL VERIFIED** — deterministic, staff-only, active leave only, no approval workflow |
| FR-06b conditional polling | **LOCAL VERIFIED** — ETag/304 + polling hook; no SSE/push |
| FR-13 routing-exclusion test | **LOCAL VERIFIED** — `test_instructor_routing.py` |
| FR-14b password-login/registration audit events | **LOCAL VERIFIED** — no passwords/secrets in audit rows |
| Backup restore rehearsal | **LOCAL VERIFIED** — status `PASS`, disposable PostgreSQL; hosted Neon restore not verified |
| Malware scanning for uploads | **LOCAL VERIFIED (INTEGRATION ONLY)** — real ClamAV clean/EICAR; disabled by default; NOT DEPLOYED |
| Working-tree Next.js e2e/accessibility suite | **LOCAL VERIFIED** — build passed, 12 passed (2.0m), no serious/critical axe violations on 3 screens |
| Hosted cron schedule / invocation (§2, §4) | **SCHEDULE VERIFIED; INVOCATION NOT VERIFIED** — live Vercel cron list shows one daily `0 0 * * *` job; no hosted invocation observed |
| npm audit after Playwright/axe install | **RESOLVED** — 0 vulnerabilities in both `npm audit` and `npm audit --omit=dev` |
| Signed scope deviation approval / formal release approval | **BLOCKED** — university approval still required; current verdict **TECHNICAL RELEASE COMPLETE; FORMAL APPROVAL PENDING** |
| Hosted secret/config verification | **PASS** (evidence in §9; live values redacted on `vercel env pull`) |
| Previously compromised OpenAI key revoked | **PASS** — provider returned `401 invalid_api_key` |
| Live end-to-end workflow (§11) | **PASS** |
| Production department seed data | **PASS** — 3 active departments seeded via audited admin API (§15) |
| No commits or pushes to Git (deployment-time, historical) | **PASS at the time**; current `origin/main` is `2cb5595ee7a38c85c63223079dc9d17a290ed089` with a clean working tree |

## 8. Conclusion

The combined hackathon deployment was executed against real hosted services. The public frontend at `https://smart-query-routing-system.netlify.app` is live, its BFF is talking to the live backend at `https://smart-query-backend.vercel.app`, and the backend is connected to the expected Neon schema. Live smoke checks passed without exposing secret values.

The deployment is suitable as a **live hackathon demonstration**, not as a formally approved production release. The unresolved governance, provider, scope, and GHCR items above must be disclosed rather than claimed as complete. The earlier reference-data FAIL was remediated and is documented in §15. The 2026-11-23 local feature work in §16 did not clear the prior FAIL verdict; the current status after the 2026-11-24 release work is **TECHNICAL RELEASE COMPLETE; FORMAL APPROVAL PENDING**, with university approval for scope/tool/model/hosting substitutions, the zero-cost interpretation, the leave workflow and public-release governance still required (§17).

---

## 9. Security verification (final sprint)

`vercel env pull` redacts every hosted value to `<SENSITIVE>`, so live secret **values** cannot be read back through the CLI. Verification therefore used the locally retained import source of truth (`render-smart-query-api.env`, never printed or committed) for value-level checks, plus live request behavior for the checks that can be observed externally.

| Check | Result | Evidence |
| --- | --- | --- |
| JWT secret freshly generated and configured | **PASS** | Present, length ≥ 48, high entropy, differs from the old compromised local `.env` value |
| BYOK encryption key valid | **PASS** | `Fernet(key)` constructs successfully |
| BYOK key rotation status | **PASS** (rotated) | Hosted key differs from the old compromised local value |
| Encrypted BYOK record compatibility | **PASS (N/A)** | 0 encrypted records exist, 0 decrypt failures; rotation CLI preserves old keys and aborts on undecryptable rows |
| Existing OpenAI key revoked | **PASS** | Direct provider probe of the old local key returned `401 invalid_api_key` |
| Global `OPENAI_API_KEY` empty | **PASS** | Import source value is empty |
| `ALLOW_GLOBAL_OPENAI_FALLBACK=false` | **PASS** | Import source value is `false`; code also blocks fallback in production |
| Database URL secure with SSL | **PASS** | `postgresql+psycopg`, Neon host, secure `sslmode`, `channel_binding` present |
| CORS only intended frontend origin | **PASS** | Live: allowed origin reflected; unknown origin receives no `Access-Control-Allow-Origin` |
| Production cookies Secure + HttpOnly | **PASS** | Live `Set-Cookie` on session: `httponly=True secure=True`; source sets `httpOnly: true` and `secure` in production (CSRF cookie is intentionally readable by client JS) |
| No secrets in deployed images | **PASS** | Both images scanned: 0 `.env`, key/cert, DB, dump, or backup files; sole pattern hit in backend `config.py` is the `change-me-local-dev` placeholder DSN |
| No secrets in Git history (deployment-time narrow scan) | **PASS at the time** | Historical scan: 307 blobs, 0 secret-pattern findings, 0 tracked `.env` files, 1 commit |
| Broader secret audit (2026-11-23) | **TRIAGE ONLY** | `docs/evidence/secret_audit.json`: 385 tracked files, 17 workspace potential secrets, 12 git-history potential secrets, 453 docker-image potential secrets, 4 current-local-env matches; no values printed, no rotation/revocation performed. See `docs/SECRET_AUDIT_REMEDIATION_PLAN.md` |

**STOP-condition assessment at deployment time:** no hosted secret or encrypted record was found unsafe; old encryption keys and encrypted user records were left untouched. The later redacted audit expands the scan surface and leaves all credential handling decisions with the owner; it does not authorize rotation or revocation.

## 10. Live BYOK test

| Check | Status |
| --- | --- |
| User securely adds own OpenAI key (encrypted before storage) | **BLOCKED** — no real user-provided key supplied; code path and encryption unit tests pass locally |
| Configured status shown without exposing value | **BLOCKED** — requires a real key through the secure UI/local secret input |
| AI ticket analysis uses that user's own key | **BLOCKED** — no real key supplied |
| No global platform key used | **PASS** — policy verified in §9 and by live 402 error below |
| Missing/invalid key produces safe error | **PASS** — live analyze call returned `402 ai_personal_key_required`: "A personal OpenAI API key is required to run AI analysis. Add one in Settings." |
| One user cannot access another user's key | **PASS (structural)** — unique `(user_id, provider)` constraint, user-scoped service reads, and 0 BYOK records for disposable users |

No real key was requested, accepted, logged, printed, or stored during this sprint.

## 11. Live end-to-end test (disposable records; all removed)

| Check | Result |
| --- | --- |
| Registration / login through BFF | **PASS** — 200, HttpOnly + Secure session cookie |
| Role permissions | **PASS** — new user is `student`; report export correctly 403 for student, 200 for admin |
| Logout + session invalidation | **PASS** — logout 200, subsequent `/me` 401 |
| CSRF missing / wrong | **PASS** — 403 / 403 |
| Ticket creation via BFF | **PASS** — 201 with a disposable department reference |
| Ticket owner read / user isolation | **PASS** — owner 200; second user 404 |
| Notification record created | **PASS** — 1 notification row for the disposable ticket |
| Multipart upload | **PASS** — 201 |
| Ticket assignment (admin) | **PASS** — 200 |
| Status workflow | **PASS** — `new → assigned → in_progress → resolved` (resolved requires a resolution summary) |
| PDF report generation | **PASS** — 200 `application/pdf`, `%PDF-` prefix |
| Cleanup | **PASS** — tickets 0, users 0, departments 0 remaining; final user count 1 (`admin:1`) |

**Historical reference-data FAIL — remediated:** at the time of this E2E run the live Neon database had 0 departments, so real ticket submission failed. At the time of that test a disposable department was created and removed to exercise the workflow. The production reference data was subsequently seeded and re-verified; see §15.

## 12. Remaining release checklist — individual dispositions

| Item | Status | Basis |
| --- | --- | --- |
| FR-04b instructor auto-routing | **LOCAL VERIFIED** | `backend/app/services/instructor_routing.py` + `backend/tests/test_instructor_routing.py`; staff-only, active leave only, no approval workflow |
| FR-06b conditional polling | **LOCAL VERIFIED** | ETag/304 `GET /tickets/{ticket_id}/updates` + `useTicketStatusPolling`; E2E polling spec. Not SSE/push |
| FR-13 routing-exclusion test coverage | **LOCAL VERIFIED** | Active-window exclusion, exclusive end boundary, workload ranking and tie-breaks tested |
| FR-14b password-login/registration audit events | **LOCAL VERIFIED** | `auth.registered`, `auth.login_succeeded`, `auth.login_failed`; `test_auth_audit.py`; no passwords/secrets |
| Database restore rehearsal | **LOCAL VERIFIED** | Disposable PostgreSQL rehearsal status `PASS` (§16); hosted Neon restore still not verified |
| Malware scanning for uploads | **LOCAL VERIFIED (INTEGRATION ONLY)** | Real ClamAV clean/EICAR checks + 10 focused tests; `MALWARE_SCAN_ENABLED=false` default; NOT DEPLOYED |
| Working-tree E2E tests | **LOCAL VERIFIED** | Playwright specs in `frontend-next/e2e/`; build passed, 12 passed (`2.0m`) |
| Accessibility tests | **LOCAL VERIFIED** | `@axe-core/playwright` on login, student workspace, ticket detail; no serious/critical violations |
| Signed university scope deviation approvals | **BLOCKED** | No signed Section L approval from VU |
| Google OAuth verification | **BLOCKED** | No real Google client ID/secret/origin supplied |
| SMTP verification | **BLOCKED** | No real SMTP credentials / `MAIL_FROM` supplied |
| WhatsApp verification | **BLOCKED** | No real Meta token, phone ID, or webhook token supplied |
| Production department seed data | **PASS** | 3 active departments seeded and verified (see §15) |
| npm audit after Playwright/axe install | **RESOLVED** | 0 vulnerabilities in both `npm audit` and `npm audit --omit=dev` |
| Hosted cron execution | **NOT VERIFIED** | Repo config and secret-protected endpoint tested locally only |

## 13. Hackathon submission package

| Artifact | Path / value |
| --- | --- |
| Project proposal PDF | `Smart_Query_Routing_Agentic_AI_Project_Proposal_Premium.pdf` |
| Deployment report PDF | `docs/HACKATHON_DEPLOYMENT_REPORT.pdf` |
| Presentation PDF | `docs/HACKATHON_DEPLOYMENT_SLIDES.pdf` (13 slides) |
| Final live frontend URL | `https://smart-query-routing-system.netlify.app` |
| Actual backend URL | `https://smart-query-backend.vercel.app` |
| Docker image URL | Docker Hub `raphicsdigitalsolutions/smart-query-system:latest` / `:v1.0.0` at current digest `sha256:2cf0a5dea54dffd643abf29a1fa7b72966899ff7235350b95fe1da793c9c2177` (anonymous pull verified; see §17). The older GHCR package `ghcr.io/raphicsdigitalsolutions/smart-query-system:latest` (`sha256:417e0170…`) is historical; GHCR publication of the release remains BLOCKED pending `write:packages` (see §5, §16 addendum) |
| LinkedIn post draft | `docs/LINKEDIN_POST_DRAFT.md` — **not published** |

**Hackathon form fields still needing manual input:** the authoritative brief (`AllProjectsS26.pdf`, pp. 30–31) contains **no submission form and no deadline**. It lists only the project description, 14 functional requirements, the tool list, and supervisor Saima Jamil. Exact form fields cannot be enumerated until the actual submission portal is supplied; team name, member names/roll numbers, supervisor acknowledgement, and the artifact links above are the likely manual entries.

## 14. GHCR permission request to owner

The saved GitHub credential has scopes `gist, repo, workflow` — **not** `write:packages`. Do not retry it. Owner action selected: create a classic GitHub token locally with only `read:packages` + `write:packages` (plus `repo` only if required for package linkage), save the token text to `C:\Users\user\AppData\Local\Temp\opencode\ghcr_pat.txt`, and confirm readiness. Never paste the token into chat. Public visibility was approved; the push workflow will set the packages public and verify manifest existence and anonymous pull before reporting an image URL.

## 15. Production department reference-data fix (approved)

**Problem:** live Neon had 0 departments → real ticket submission returned `400 "No active department matched this request"`.

**Source determination:** neither the university brief (`AllProjectsS26.pdf`, pp. 30–31) nor the project proposal PDF enumerates department names. The only code-sourced names are the project's own test fixtures, `backend/tests/conftest.py` (the evaluation dataset is explicitly synthetic and was rejected as a production source). The owner approved those three fixture records and approved the audited admin-API method. No names or IDs were invented; the database assigned IDs.

**Exact records written (approved):**

| id (DB-assigned) | name | description | is_active |
| --- | --- | --- | --- |
| 3 | `Registry` | `Student records` | true |
| 4 | `Scholarships` | `Awards` | true |
| 5 | `IT Services` | `Technology support` | true |

**Method:** `POST /api/v1/departments` through the live frontend BFF with a short-lived admin token; the existing service performs a case-insensitive duplicate check, sets `is_active=true`, and writes an audited `department.created` record. Re-posting `Registry` returned **409**, confirming idempotency. Equivalent SQL (not executed; shown for the record):

```sql
INSERT INTO departments (name, description, is_active)
SELECT v.name, v.description, TRUE
FROM (VALUES
  ('Registry', 'Student records'),
  ('Scholarships', 'Awards'),
  ('IT Services', 'Technology support')
) AS v(name, description)
WHERE NOT EXISTS (
  SELECT 1 FROM departments d WHERE lower(d.name) = lower(v.name)
)
ON CONFLICT (name) DO NOTHING;
```

**Live verification through the public frontend:**

| Check | Result |
| --- | --- |
| Existing departments read via BFF before seed | 200, 0 rows |
| Seed `Registry`, `Scholarships`, `IT Services` | 201 / 201 / 201 |
| Duplicate `Registry` re-post | 409 (no duplicate created) |
| Active department count after seed | 3 of 3 |
| Ticket with explicit `department_id=Registry` | 201, `department_name=Registry` |
| Auto-route "Scholarship award eligibility query" | 201, routed to `Scholarships` |
| Auto-route "Technology support request" | 201, routed to `IT Services` |
| Ticket retrieval via frontend | 200, `department_name=Registry` |
| Ticket assignment via frontend (admin) | 200 |
| Admin retrieval of assigned ticket | 200 |
| Cleanup | disposable tickets 0, users 0 remaining |

**Final state:** 3 active departments, 3 `department.created` audit records, 1 user (the original admin), 0 tickets. No existing user, ticket, or other record was modified or deleted. No source code was changed.

---

## 16. Local-only reconciliation evidence (2026-11-23)

All items in this section are **LOCAL VERIFIED** unless otherwise marked. Nothing here changes the
live deployment, provider configuration, credentials, GHCR content or production database.

### Feature delivery

- **FR-04b / FR-13:** `backend/app/services/instructor_routing.py` selects deterministically from
  active `staff` users in the resolved department, excludes active `InstructorLeave` windows
  (exclusive end bound) and inactive users, never auto-assigns HOD/admin users, and ranks by
  non-terminal workload then lowercase name then ID. No approval workflow exists; absence of an
  eligible instructor leaves the ticket in `new` with an audit row. Tests:
  `backend/tests/test_instructor_routing.py`.
- **FR-06:** `GET /api/v1/tickets/{ticket_id}/updates` returns a status snapshot with `ETag` and
  `Cache-Control: no-store`, or HTTP 304 for a matching `If-None-Match`. The frontend
  `useTicketStatusPolling` hook polls about every 15 seconds; this is not SSE or push. E2E polling
  spec: `frontend-next/e2e/tickets.spec.ts`.
- **FR-07:** `POST /api/v1/tickets/escalation/sweep` requires `X-Cron-Secret` and fails closed
  (503 `escalation_cron_not_configured`, 401 `invalid_cron_secret`). `backend/vercel.json` schedules
  it daily (`0 0 * * *`), matching the one job in the live cron list. Tests:
  `backend/tests/test_escalation_serverless.py`. **Actual hosted invocation is NOT VERIFIED.**
- **FR-14:** `auth.registered`, `auth.login_succeeded` and `auth.login_failed` audit events are
  written with email/reason context and no password or secret (`backend/tests/test_auth_audit.py`).
- **Token lifetime:** production default 60 minutes; test-only 1440 minutes
  (`backend/tests/test_token_expiry.py`).

### Verification evidence

- Backend full suite historical runs: 218 passed, 225 passed. **Final full backend suite: 229 passed, 17 warnings in
  410.30s (0:06:50), 0 failed/errors**; focused security/auth/malware/cron run `64 passed`; focused escalation/notification run `42 passed`; warnings are pre-existing LangSmith deprecations. Historical results remain
  in `docs/TEST_REPORT.md`.
- Playwright + axe: build passed (`12/12` pages, webpack); **12 tests passed in 2.0m**; Vitest `3 passed`; lint/typecheck PASS; no serious/critical axe violations on
  login, student workspace or ticket detail. Local browser run only, not a hosted verification.
- Backup/restore rehearsal: `docs/evidence/backup_restore_rehearsal.json`, status `PASS`, using a
  disposable `postgres:16-alpine` container at `127.0.0.1:55432`; schema hash
  `ed7d1ab744886956c3e35ddde4674a05b01da26ef8313199b2c741e35917664b`, record hash
  `00e07e9f6182a27c59db5e2b9b0d51055011c13029485c4647b9ba4cc994d419`, stale row count 1 → 0,
  container removed. No production data touched; hosted Neon restore not verified.
- Malware scanning: `docs/evidence/malware_scan_verification.json`, status
  `PASS_LOCAL_INTEGRATION_ONLY`. Real `clamav/clamav:stable` image digest
  `sha256:64e30c0bf976198024deb3dc6d5cfe2485fb969c0f73549ba0fdb364b9469614` returned clean `OK`
  (exit 0) and EICAR `FOUND` (exit 1) with in-container base64 fixtures; 10 focused tests passed.
  `MALWARE_SCAN_ENABLED=false` by default; no scanner is configured in the hosted environment and
  a Windows mount fixture failed. **NOT DEPLOYED.**
- Secret audit: `docs/evidence/secret_audit.json` and `docs/SECRET_AUDIT_REMEDIATION_PLAN.md`
  report 385 tracked files, 17 workspace potential secrets, 12 git-history potential secrets,
  453 docker-image potential secrets and 4 matches against current local environment values. The
  evidence stores redacted field names/lengths/fingerprints, never values. **No rotation or
  revocation was authorized or performed.**
- `npm audit` after Playwright/axe install: 6 vulnerabilities (2 moderate, 2 high, 2 critical) —
  historical finding, fully remediated on 2026-11-24; both audits now report 0 vulnerabilities.

### Still blocked or outstanding

- GHCR publication remains **BLOCKED** (missing `write:packages`). Registry content, including
  `ghcr.io/raphicsdigitalsolutions/smart-query-system:latest`, was left untouched. The unified Supervisor image was published to Docker Hub instead (see §17).
- Live Google OAuth, SMTP, WhatsApp, real-user BYOK, hosted cron invocation, hosted restore/malware scanner, monitoring and retention remain **NOT VERIFIED** without real credentials or operator confirmation.
- University approval is still required for scope deviations, tool/model/hosting substitutions, the
  zero-cost interpretation, the leave workflow and release/public governance. Current verdict:
  **TECHNICAL RELEASE COMPLETE; FORMAL APPROVAL PENDING**.

### 2026-11-23 read-only GHCR addendum

The 2026-11-22 "remote manifests missing" wording in §§4 and 16 is superseded for one package by a
read-only investigation (`docs/evidence/ghcr_readonly_investigation.json`):
`ghcr.io/raphicsdigitalsolutions/smart-query-system:latest` exists, returns an anonymous token and
manifest with HTTP 200, and has OCI index digest
`sha256:417e017081a460adfe310236e13b3e117cb972c11c5c93370968aa866a2b0f0f`, matching the recorded
and local digests. No registry write or push was performed. Publication of the current local changes
still requires `write:packages`, and separate `smart-query-backend` / `smart-query-frontend` packages
were not verified. The generated PDF retains the historical wording; this addendum is current.

### 2026-11-24 local dependency remediation addendum

- All 6 frontend dependency vulnerabilities were resolved locally (`vitest@4.1.12`, `zod@4.6.7`, `next@16.4.6`, `eslint-config-next@16.4.6`, `next build --webpack`) with `0 vulnerabilities` across both `npm audit` and `npm audit --omit=dev`.
- Final local suites passed: backend **229 passed, 17 warnings in 410.30s (0:06:50)**, 0 failed/errors; Vitest **3 passed**; lint/typecheck **PASS**; build **PASS** (Next.js 16.4.6 webpack, `12/12` pages); Playwright + Axe **12 passed (2.0m)**; Compose configs and `docker build --check` **PASS**; Alembic head/current `feedf21773e1` and `check` clean. No live Netlify redeploy was executed.

---

## 17. Final 2026-11-24 release verification (current state)

Authoritative evidence: `docs/evidence/phase5_live_verification_2026-11-24.json`. The prior `FAIL — DO NOT DEPLOY` wording in this report is historical; the current verdict is **TECHNICAL RELEASE COMPLETE; FORMAL APPROVAL PENDING**.

- **Git:** `origin/main` is `2cb5595ee7a38c85c63223079dc9d17a290ed089`; chain `b51dd31` → `7ad663e` (daily cron + Phase 1/2 evidence) → `eb30f92` (Docker Hub evidence) → `2cb5595` (live verification evidence). Working tree was clean after that commit.
- **Vercel backend:** deployment `dpl_CRo9kXq4CBL8p8oSaaAyKdSjNVoM`, READY, target `production`, source CLI, aliases `smart-query-backend.vercel.app` and `smart-query-backend-inforaphicsdigital-8444.vercel.app`. Metadata commit `b51dd31` with a dirty CLI working tree; the deployed config already contains the daily cron and current main matches. Hobby permits at most once/day, so the final schedule is `0 0 * * *` for `/api/v1/tickets/escalation/sweep`; the live cron list shows exactly that one job. Schedule existence is verified; actual hosted invocation is **NOT VERIFIED**. Live `/health`, `/api/v1/status` and `/api/v1/status/database` returned HTTP 200; `/api/v1/departments` returned HTTP 401 as expected.
- **Netlify frontend:** public root and `/api/health` returned HTTP 200. Authenticated deploy state and source sync are **NOT VERIFIED** (no token; API 401). Live HTML uses Turbopack chunks while current main builds with webpack after commit `75d6f16`; do **not** claim the live site matches current main. Deploy ID `6b02db1360e3188d7f1074c6` could not be authenticated or confirmed. Owner action: confirm/redeploy from GitHub main. No redeploy was performed.
- **release-v1 database (read-only):** `neondb`, URL fingerprint `5d1fc726d19b`, host fingerprint `141f6064ec7f`, Alembic `feedf21773e1`, 17 public tables, 4 departments, 0 users, 0 tickets, no writes. Branch identity comes from the operator-provided, git-ignored `backend/.env.release_v1` file name; Vercel sensitive values were withheld and the Neon UI was unavailable, so direct equality with the hosted database and any old DB state are **NOT VERIFIED**.
- **Docker Hub:** `raphicsdigitalsolutions/smart-query-system` tags `latest` and `v1.0.0` at digest `sha256:2cf0a5dea54dffd643abf29a1fa7b72966899ff7235350b95fe1da793c9c2177`, matching the local image (the older `sha256:e9ed708…` digest is stale). Anonymous pull with a temporary empty Docker config exited 0 and the anonymous manifest returned HTTP 200. Container smoke: healthy, UID 10001, Supervisor backend+frontend RUNNING, 4 HTTP checks 200 with disposable SQLite and no external integrations; no `.env` or key files in the image.
- **NOT VERIFIED:** Google OAuth, SMTP, Meta WhatsApp, real-user BYOK, hosted cron invocation, university approval, hosted restore/malware scanner, and monitoring/retention. Common root and `/api/health` smoke results do not prove source sync or formal release approval.
