# Release Readiness — Final Pre-Deployment Audit

**Project:** Smart Query Routing & Email Automation System  
**Original audit date:** 2026-11-22 (historical)  
**Final reconciled:** 2026-11-24 — release artifacts, final test reruns, live backend/Netlify checks, daily cron schedule, Docker Hub publication, and `release-v1` read-only database verification are recorded below. Final evidence is indexed in §10 of `docs/TEST_REPORT.md`. The historical `FAIL — DO NOT DEPLOY` current-state verdicts in this document are superseded; the current status is **TECHNICAL RELEASE COMPLETE; FORMAL APPROVAL PENDING**.  
**Scope:** Code/config/documentation audit, security remediation, verification, and release decision.  
**Actions explicitly not performed:** no credential change, no database write, no formal institutional sign-off, no Netlify redeploy, and no modification of values in `backend/.env`.

> **Release addendum (2026-11-24):** A live hackathon deployment was executed on Netlify, Vercel, and Neon, and its technical artifacts are published and verified. Formal institutional/governance approval, live provider verification, hosted cron invocation, Netlify deploy/source confirmation, and operator secret review remain open. release-evidence commit is `2cb5595ee7a38c85c63223079dc9d17a290ed089` (`b51dd31` → `7ad663e` → `eb30f92` → `2cb5595`), with a clean working tree after the final commit. See `docs/HACKATHON_DEPLOYMENT_REPORT.md` for the original deployment record and `docs/TEST_REPORT.md` §10 for final evidence.

## 1. Decision

| Release target | Decision | Reason |
| --- | --- | --- |
| Technical release / live hackathon demonstration | **TECHNICAL RELEASE COMPLETE** | `origin/main` `2cb5595...` is clean and verified; Vercel production deployment `dpl_CRo9kXq4CBL8p8oSaaAyKdSjNVoM` is READY with live backend smoke checks passing; Docker Hub `latest`/`v1.0.0` publish digest `sha256:2cf0a5dea54dffd643abf29a1fa7b72966899ff7235350b95fe1da793c9c2177` with anonymous pull verified; final backend suite **229 passed, 17 warnings in 410.30s (0:06:50)**; frontend Vitest **3 passed**, typecheck/lint/build PASS (Next.js 16.4.6 webpack, **12/12** pages), Playwright + axe **12 passed in 2.0m** with no serious/critical violations, `npm audit` and `npm audit --omit=dev` **0 vulnerabilities**; daily `0 0 * * *` cron schedule verified; `release-v1` database verified read-only with `writes_performed=false`. |
| Formal production / institutional release | **FORMAL APPROVAL PENDING — LIVE DEMONSTRATION; FORMAL SIGN-OFF NOT VERIFIED** | Formal institutional/governance sign-off and signed scope deviations are not on file; Google OAuth, SMTP, Meta WhatsApp, real-user OpenAI BYOK, hosted cron invocation, hosted restore/malware scanner, monitoring/retention, and Netlify authenticated deploy state/source sync are **NOT VERIFIED**; four historical current-local secret candidates still require owner review; published Vercel-to-`release-v1` `.env` database equality is **NOT CLAIMED**; the original production database was previously checked read-only and not modified. |

The code-level remediation and technical verification are complete. The remaining items are formal
approval, live provider verification, operator-controlled secret review, and Netlify owner
confirmation — not code defects. Earlier `FAIL — DO NOT DEPLOY` language in this document is
historical and superseded by this decision.

## 2. Authority and scope baseline

- The authoritative original brief is `C:\Users\user\Downloads\AllProjectsS26.pdf`.
- The in-repo `Smart_Query_Routing_Agentic_AI_Project_Proposal_Premium.pdf` is a derived blueprint with conflicting FR IDs. It is not institutional approval and does not silently supersede the original brief.
- OpenAI with per-user BYOK remains the implemented provider; production global fallback is forbidden.
- **Historical planning note:** the original audit assumed Vercel would host only `frontend-next` as the frontend/BFF and could not host the FastAPI container, PostgreSQL, the external volume, or the full Compose stack. In the subsequent hackathon deployment the FastAPI backend was deployed to Vercel as serverless functions (deployment `dpl_CRo9kXq4CBL8p8oSaaAyKdSjNVoM`), with PostgreSQL on Neon and the Next.js BFF on Netlify; the full Compose stack was not deployed there.
- Section L of `docs/MASTER_REQUIREMENTS_CHECKLIST.md` has nine rows (L-01–L-09); all are reported in §7.

## 3. Secret findings — redacted

Final evidence is `docs/evidence/secret_audit.json` and `docs/SECRET_AUDIT_REMEDIATION_PLAN.md` (2026-11-23). No value was printed, copied, logged, or modified. The evidence stores only field names, locations, classifications, value lengths, and 12-character SHA-256 fingerprints — not usable credentials.

| Scope / metric | Count | Interpretation |
| --- | ---: | --- |
| Tracked files scanned | 307 | Current tracked source tree. |
| Workspace findings classified `potential_secret` | 16 | Mostly field-name/literal patterns in source and tests. |
| Git-history findings classified `potential_secret` | 12 | Same code-pattern class as the tracked findings; no current-local value found in history. |
| Container-image findings classified `potential_secret` | 453 | Overwhelmingly dependency/source identifiers; no current-local value matched any image. |
| Fingerprints matching current local environment values | 4 | The only findings requiring possible credential-handling action. |

| ID | Evidence (redacted) | Pattern class | Severity | Status |
| --- | --- | --- | --- | --- |
| SEC-01 | `backend/.env:42` — `OPENAI_API_KEY` | Likely live provider key pattern | Critical | **Not rotated/revoked.** Owner approval required to revoke at OpenAI and store a replacement in a secret manager. |
| SEC-02 | `backend/.env:51` — `BYOK_ENCRYPTION_KEY` | Valid Fernet-key shape | High | **Not rotated.** Owner approval and the staged re-encryption procedure in §6 are required before replacing the configured value. |
| SEC-03 | `backend/.env.local:2` — `VERCEL_OIDC_TOKEN` | Provider-issued token | High | **Not revoked/reissued.** Reissue only through the provider with owner approval. |
| SEC-04 | `backend/.env:17` — `DATABASE_URL` | Local database connection string | Review | Owner review required; do not rotate a database credential without approval. |
| INFO-01 | `backend/tests/conftest.py`, `backend/tests/test_byok.py`, E2E config | Synthetic test fixtures, including test-only `ACCESS_TOKEN_EXPIRE_MINUTES=1440` | Informational | Test-only; the production default of 60 minutes is asserted by `backend/tests/test_token_expiry.py`. No production setting changed. |
| INFO-02 | `.env.example`, `backend/.env.example` | `REPLACE_WITH_*`, example domains, known development keys | Informational | Safe samples remain tracked by design; strict production validation rejects them. |

`JWT_SECRET_KEY` in `backend/.env` / `backend/.env.example` and `SMTP_PASSWORD` in `backend/.env` were reclassified as placeholder/reference values and are not among the four current-local matches. The BYOK implementation reviewed in `app/core/encryption.py`, `app/services/byok.py`, `app/api/routes/settings.py`, and `app/models/user_api_key.py` is Fernet-encrypted, user-scoped, unique per `(user_id, provider)`, not returned by status APIs, not logged, and resolved from the requesting user during AI runs. **No rotation or revocation was authorised or performed.**

### `release-v1` database isolation (2026-11-24)

`docs/evidence/release_v1_readonly_verification_2026-11-24.json` records a **read-only** verification
of the isolated `release-v1` branch database: database `neondb`, URL fingerprint
`sha256_12 5d1fc726d19b`, host fingerprint `141f6064ec7f`, Alembic revision `feedf21773e1`, 17 public
tables, `departments=4`, `users=0`, `tickets=0`, and `writes_performed=false`. Branch identity came
from the operator-provided, git-ignored **`backend/.env.release_v1` file name**. Vercel withholds
sensitive `DATABASE_URL` values and the Neon UI was unavailable, so **direct Vercel-to-`.env`
equality is not claimed, and the original production database state was not re-checked here; that
database was previously checked read-only and was not modified**. This verification does not rotate or
expose any credential.

### Finding classification (2026-11-23)

| Class | Findings | Disposition |
| --- | --- | --- |
| Actual-secret candidate — treat as real until owner review | 4 current-local matches: `OPENAI_API_KEY` (`089ee82c29af`), `BYOK_ENCRYPTION_KEY` (`f70b8084e710`), `VERCEL_OIDC_TOKEN` (`3e0e10366f60`), `DATABASE_URL` (`c1271fe222ae`) | Owner decision and, if approved, rotation/revocation pending. These are fingerprints only; no value was printed. |
| Test fixture | Synthetic test keys/tokens including `ACCESS_TOKEN_EXPIRE_MINUTES=1440` in `backend/tests/conftest.py` and E2E config | Informational; production default 60 minutes is asserted by `backend/tests/test_token_expiry.py`. |
| False positive / safe sample | `.env.example` files, `JWT_SECRET_KEY`/`SMTP_PASSWORD` reference values, dependency and source identifiers in images | Not credentials; placeholders are rejected by strict production validation. |
| Historical credential pattern | 12 Git-history `potential_secret` findings in commit `6f388d0` | Code-pattern matches only; no current-local value was found in history. |
| Pattern-only bulk matches | Workspace 105 findings = 36 placeholder/reference, 16 potential, 53 short/unknown; image 453 potential matches | No current-local value matched any image. |

Full triage, the staged BYOK backup/re-encryption/rollback plan, and the explicit non-actions are in
`docs/SECRET_AUDIT_REMEDIATION_PLAN.md`. No rotation or revocation was authorised or performed.

### Git repository and working-tree audit

**Historical audit state:** Git was initialized with one local commit (`6f388d0`) and an `origin` remote; the read-only working-tree audit covered 385 tracked files, and the redacted audit scanned 385 tracked files plus reachable Git history, recording 12 `potential_secret` code-pattern findings with no current-local environment value in history. No push, branch, tag, or registry change was performed by those audits. **Current state (2026-11-24):** release-evidence commit is `2cb5595ee7a38c85c63223079dc9d17a290ed089`, with the chain `b51dd31` → `7ad663e` → `eb30f92` → `2cb5595` and a clean working tree after that commit. The operator must still review the redacted fingerprints in `docs/evidence/secret_audit.json`, re-run `git status --ignored`, and confirm `backend/.env`, `backend/.env.local`, and `backend/.env.release_v1` are ignored. Never use `git add -f` on environment files.

## 4. Code and configuration fixes applied

| ID | Fix | Files | Verification |
| --- | --- | --- | --- |
| FIX-01 | Comprehensive ignore rules for all `.env` files except safe samples, runtime attachment storage, generated evaluation reports, logs, databases, keys/certificates, archives, temp/swap files, caches, and build artifacts | `.gitignore` | `tests/test_release_hardening.py::test_gitignore_covers_release_artifacts_but_keeps_samples` |
| FIX-02 | Docker build-context hardening, including recursive Python cache exclusion and `eval_reports/` exclusion | `.dockerignore`, `backend/.dockerignore`, `frontend-next/.dockerignore` | Rebuild context dropped from 93.72 kB to 5.82 kB; rebuilt backend image has no `.pyc` files |
| FIX-03 | Strict fail-closed production validation | `backend/app/core/config.py` | 25 regression cases in `tests/test_release_hardening.py` |
| FIX-04 | Safe BYOK Fernet rotation CLI with dry-run, all-row pre-decryption, one-transaction re-encryption, verification, rollback, and no key output | `backend/app/cli/rotate_byok_encryption_key.py` | `tests/test_byok_rotation.py` |
| FIX-05 | Raw provider exception text no longer stored in `Notification.last_error` or returned by the debug error handler | `backend/app/core/errors.py`, `backend/app/services/email.py`, `backend/app/services/whatsapp.py`, `backend/app/main.py` | Sanitizer unit test plus notification regression assertions |
| FIX-06 | BYOK plaintext cap reduced so Fernet ciphertext fits the 512-character DB column | `backend/app/schemas/byok.py`, `backend/app/services/byok.py` | `tests/test_byok.py::test_maximum_key_length_fits_encrypted_column` |
| FIX-07 | Documentation corrected: production validation, WhatsApp GET handshake, safe rotation procedure, Phase 7 status, final counts, and known gaps | `docs/DEPLOYMENT_GUIDE.md`, `docs/TEST_REPORT.md`, `docs/MASTER_REQUIREMENTS_CHECKLIST.md`, `docs/PROJECT_OVERVIEW.md`, `README.md` | File review and final verification rerun |

### Strict production validation

When `ENVIRONMENT=production`, startup now rejects:

- `DEBUG=true`
- `ALLOW_GLOBAL_OPENAI_FALLBACK=true`
- `JWT_ALGORITHM` other than `HS256`
- missing, placeholder, known-development, short, or low-entropy `JWT_SECRET_KEY`
- missing, placeholder, known-development, or invalid Fernet `BYOK_ENCRYPTION_KEY`
- non-PostgreSQL `DATABASE_URL`
- placeholder database username/password or password shorter than 12 characters
- localhost production database hosts
- external database URLs without `sslmode=require|verify-ca|verify-full` (the internal Compose host `postgres` remains the narrow exception)
- wildcard, localhost, or placeholder CORS origins
- placeholder `MAIL_FROM` when email notifications are enabled
- placeholder Google OAuth client ID when Google OAuth is enabled
- placeholder WhatsApp credentials when WhatsApp is enabled
- placeholder `INTAKE_WEBHOOK_TOKEN`

Error messages name the failing setting but never include its value. Local development defaults remain functional.

## 5. Verification evidence

The original hardening checks below were executed locally. The 2026-11-24 final verification additionally performed read-only checks against public Vercel/Netlify/Docker Hub/Neon endpoints; see §9 and `docs/TEST_REPORT.md` §10. No database write, credential change, or redeploy was performed.

| Area | Command / method | Result |
| --- | --- | --- |
| Full backend suite | `.\.venv\Scripts\python.exe -m pytest -q` (from `backend/`) | **Final rerun: 229 passed, 17 warnings in 410.30s (0:06:50)**, 0 failed/errors (`docs/evidence/final_backend_test.json`). Historical runs: 187, 202, 218, 225 passed and earlier 264.12s/292.01s timings. Focused security/auth/malware/cron run: `64 passed, 17 warnings in 27.06s`; focused escalation/ticket/notification/audit run: `42 passed, 17 warnings in 70.95s`; focused AI/BYOK/knowledge/eval run: `50 passed, 17 warnings in 32.74s`. Warnings are pre-existing LangSmith `asyncio.iscoroutinefunction` deprecations. |
| New hardening regressions | `python -m pytest -q tests/test_release_hardening.py tests/test_byok_rotation.py tests/test_notifications.py` | `38 passed, 17 warnings in 20.72s` (plus included in the final 229-passed backend run and 64-passed security/auth/malware/cron run). |
| Frontend Playwright + axe E2E | `npm run test:e2e` after successful `npm run build` | **12 passed in 2.0m** (`docs/evidence/e2e_axe_result.json`); auth, ticket submission/polling/isolation, manual escalation/de-escalation history & notifications, and axe scans of login, student workspace, and ticket detail; no serious/critical axe violations. Vitest polling tests: **3 passed**. |
| Backup/restore rehearsal | `scripts/backup_restore_rehearsal.ps1` with disposable `postgres:16-alpine` on `127.0.0.1:55432` | `docs/evidence/backup_restore_rehearsal.json` status **PASS** (re-executed `2026-11-23T16:57:24Z` with `DEBUG=false` override); schema hash `ed7d1ab744886956c3e35ddde4674a05b01da26ef8313199b2c741e35917664b`; record hash `00e07e9f6182a27c59db5e2b9b0d51055011c13029485c4647b9ba4cc994d419`; stale row count 1→0; container removed; `production_touched: false`. |
| Malware scan local integration | real ClamAV `clamscan --no-summary` (`ClamAV 1.5.5/28191`, `clamav/clamav:stable`) + focused pytest | `docs/evidence/malware_scan_verification.json` status `PASS_LOCAL_INTEGRATION_ONLY`; re-verified clean `/tmp/c.txt: OK` (exit 0) and `Eicar-Test-Signature FOUND` (exit 1); image digest `sha256:64e30c0bf976198024deb3dc6d5cfe2485fb969c0f73549ba0fdb364b9469614`; focused `test_malware_scan_service.py` + `test_attachment_malware.py` tests pass (`10 passed` covering clean, infected->422, unavailable/error->503, timeout->503). Default `MALWARE_SCAN_ENABLED=false`, not deployed; Windows-mounted EICAR fixture failed (exit 2) and is not a pass. |
| Dependency audit | `npm audit --json` and `npm audit --omit=dev --json` from `frontend-next/` | **Final: 0 vulnerabilities** (`docs/evidence/npm_audit_final_2026-11-24.json`, `npm_audit_prod_final_2026-11-24.json`). The 6-package result in `npm_audit_summary.json` is historical; the Next.js 16.4.6/Zod 4.6.7/Vitest 4.1.12 upgrades were applied and re-verified. |
| Frontend typecheck | `npm run typecheck` (from `frontend-next/`) | Exit 0. |
| Frontend lint | `npm run lint` | Exit 0. |
| Frontend build | `npm run build` (`next build --webpack`, Next.js 16.4.6) | Exit 0; 12/12 static pages generated. |
| Compose | `docker compose -f docker-compose.db.yml config --quiet`; `docker compose -f docker-compose.yml config --quiet` | Both exit 0. `docker build --check .` reported no warnings. |
| Backend image | `docker build -t smartquery-backend:release-audit ./backend` | Exit 0. |
| Frontend image | `docker build -t smartquery-frontend:release-audit ./frontend-next` | Exit 0. |
| Redacted secret audit | `python scripts/secret_audit.py` | 385 tracked files scanned; workspace potential 16, Git-history potential 12, container-image potential 453, current-local-env matches 4. Redacted fingerprints only; no value printed or changed; no rotation/revocation. See §3. |
| Git repository / history audit | `git rev-parse`, `git status --short --untracked-files=all`, `git log`, `git remote -v`, read-only history scans | Historically one local commit (`6f388d0`); 385 tracked files and reachable history were scanned, with 12 potential-secret code-pattern findings and no current-local value in history. Current state: release-evidence commit `2cb5595ee7a38c85c63223079dc9d17a290ed089` (`b51dd31` → `7ad663e` → `eb30f92` → `2cb5595`), clean working tree after that commit. No push or remote change was performed by these audits. |
| Alembic final check | `alembic heads`; `alembic current`; `alembic check` | Heads/current `feedf21773e1`; `alembic check` clean. |
| Vercel backend (read-only) | Deployment listing and live smoke | `dpl_CRo9kXq4CBL8p8oSaaAyKdSjNVoM` READY, production, CLI source; aliases `smart-query-backend.vercel.app` and `smart-query-backend-inforaphicsdigital-8444.vercel.app`. Live `/health` 200 `healthy`, `/api/v1/status` 200 version `1.0.0`, `/api/v1/status/database` 200 `connected`, `/api/v1/departments` 401 (expected). Exactly one daily `0 0 * * *` cron for `/api/v1/tickets/escalation/sweep`; invocation NOT VERIFIED. |
| Netlify frontend (read-only) | Public HTTP checks | `https://smart-query-routing-system.netlify.app` `/` and `/api/health` 200, `Server: Netlify`. Authenticated deploy state/source sync NOT VERIFIED (no token, API 401; live Turbopack chunks vs webpack on current main; deploy ID `6b02db1360e3188d7f1074c6` unconfirmed). No redeploy performed. |
| `release-v1` database (read-only) | Fingerprint/row-count verification | `neondb`, URL `sha256_12 5d1fc726d19b`, host `141f6064ec7f`, Alembic `feedf21773e1`, 17 public tables, `departments=4`, `users=0`, `tickets=0`, `writes_performed=false`; branch identity from the git-ignored `backend/.env.release_v1` file name only. |
| Docker Hub release (read-only) | Tag/digest and anonymous pull checks | `raphicsdigitalsolutions/smart-query-system:latest` and `:v1.0.0` both `sha256:2cf0a5dea54dffd643abf29a1fa7b72966899ff7235350b95fe1da793c9c2177`, matching local RepoDigests; anonymous pull (empty Docker config) exit 0; manifest HTTP 200. |

Additional previous evidence remains in `docs/TEST_REPORT.md`: 41 OpenAPI paths, disposable container smoke tests, BFF session/401 checks, and PostgreSQL restart persistence using scratch resources that were removed afterward. The existing `smartquery-postgres` container and its external volume were not recreated, stopped, or deleted.

## 6. Docker image content audit

| Check | Backend `release-audit` | Frontend `release-audit` |
| --- | --- | --- |
| `.env` / `.env.*` files | None | None |
| `*.pem`, `*.key`, `*.p12`, `*.pfx`, npmrc/pypirc | None | None |
| Database/log/backup/temp files | None | None |
| Generated reports, attachment bytes, tests | None | Not applicable |
| `.pyc` files after recursive ignore fix | None | Not applicable |
| Secret-pattern grep (`sk-proj-`, `gAAAAA`, private-key header, AWS/Google key shapes) | No matching files in the 2026-11-22 scan | No matching files in the 2026-11-22 scan |
| Runtime user / workdir | `app` / `/app` | `nextjs` / `/app` |

The first backend build exposed host-generated `.pyc` files because `backend/.dockerignore` used only non-recursive cache patterns. This was fixed with `**/__pycache__/` and `**/*.py[cod]`, and the rebuilt image was re-inspected cleanly.

The broader 2026-11-23 redacted audit (`docs/evidence/secret_audit.json`) classifies 453 container-image findings as `potential_secret`; these are overwhelmingly dependency and source-code identifier patterns, with no current-local environment value matching any image. The two scans use different heuristics; neither changed any image or registry content. The final combined Docker Hub image was re-inspected: no `.env` or key files; the remaining pattern matches were Next.js documentation/library strings only.

## 7. Requirement reconciliation and remaining scope gaps

Of the nine Section L rows, L-01–L-03 are locally completed; L-09 now has a live technical
deployment, while formal institutional approval remains pending:

| ID | Item | Status |
| --- | --- | --- |
| L-01 | Instructor-level automatic routing | Completed locally — deterministic staff-only, leave-aware routing; no HOD/admin auto-assignment and no approval workflow. |
| L-02 | Live status polling/SSE | Completed for polling — conditional ETag/304 endpoint + `useTicketStatusPolling` hook + E2E case; SSE/push is not implemented and is not claimed. |
| L-03 | Password-login/registration audit events | Completed — success/failure events without passwords/secrets; `tests/test_auth_audit.py` passes. |
| L-04 | Google OAuth live verification | Blocked — real client ID/origin unavailable. |
| L-05 | SMTP live verification | Blocked — real credentials and verified `MAIL_FROM` unavailable. |
| L-06 | WhatsApp live verification | Blocked — real Meta token/phone ID/webhook token unavailable. |
| L-07 | OpenAI live evaluation/live key validation | Blocked — real user personal key unavailable; no global fallback. |
| L-08 | Zero-cost/Gemini+Claude/n8n/Baileys/Sheets toolchain | Blocked — conflicts with approved OpenAI/FastAPI/local DB architecture. |
| L-09 | Public deployment | Live hackathon technical deployment executed and verified (Vercel/Netlify/Neon); formal institutional approval and signed scope deviations still pending. Netlify source sync is NOT verified. |

Additional audit corrections recorded in `docs/MASTER_REQUIREMENTS_CHECKLIST.md` Sections M and O include overstated statuses for A-FR-13, A-DFR-12, A-DFR-13, A-SEC-01, A-SEC-04, A-SEC-05, A-QA-02, I-02, I-03, I-06–I-09. There is no signed supervisor/scope deviation approval in the repository.

Local verification added after the original audit (2026-11-23/24), summarized in `docs/MASTER_REQUIREMENTS_CHECKLIST.md` Section O:

- Final full backend suite rerun: **229 passed, 17 pre-existing LangSmith warnings in 410.30s (0:06:50)** (earlier 187, 202, 218, 225 runs and 264.12s/292.01s timings are historical evidence); plus focused runs of `64 passed` (security/auth/malware/cron), `42 passed` (escalation/ticket/notification/audit), and `50 passed` (AI/BYOK/knowledge/eval).
- Deterministic instructor routing, conditional polling, manual/auto escalation & de-escalation history and deduplicated notification fanout, and password-auth audit events are implemented and locally tested.
- Restore rehearsal PASS (`2026-11-23T16:57:24Z`) on a disposable PostgreSQL container; production volume untouched.
- Real ClamAV (`ClamAV 1.5.5/28191`) local integration PASS (`PASS_LOCAL_INTEGRATION_ONLY`), default disabled and not deployed; the Windows-mounted EICAR fixture failed (exit 2) and is not a pass.
- Playwright + axe E2E: **12 passed in 2.0m**, Vitest **3 passed**, no serious/critical violations on login, student workspace, or ticket detail; frontend build uses Next.js 16.4.6 webpack with 12/12 static pages.
- Redacted secret audit triage is complete; no rotation/revocation. The 12 Git-history and 453 image findings are code/dependency patterns; 4 current-local matches require owner action.
- `npm audit` and `npm audit --omit=dev` now report **0 vulnerabilities** after the applied Next.js/Zod/Vitest upgrades. Docker Hub `latest`/`v1.0.0` publish digest `sha256:2cf0a5dea54dffd643abf29a1fa7b72966899ff7235350b95fe1da793c9c2177`; the historical GHCR read-only check used a different digest, and GHCR publication still lacks `write:packages`. Only the daily cron schedule is verified; hosted invocation is NOT VERIFIED. See `docs/TEST_REPORT.md` §10.

## 8. Operator actions still required before formal release

These actions require owner/provider access and were intentionally not performed. The technical
release work itself is complete; these are governance/verification items.

1. **Obtain institutional sign-off** for the OpenAI/BYOK substitution, the Section L gaps, and the formal production release. No university/institutional approval is on file.
2. **Owner review of the historical four current-local secret candidates** (`OPENAI_API_KEY` at `backend/.env:42`, `BYOK_ENCRYPTION_KEY` at `backend/.env:51`, `VERCEL_OIDC_TOKEN`, `DATABASE_URL`) using the redacted fingerprints in `docs/evidence/secret_audit.json`. No value was printed, rotated, or revoked here; rotation is an owner decision, including the staged BYOK procedure in `DEPLOYMENT_GUIDE.md` §11.1.
3. **Git review.** Current release-evidence commit is `2cb5595ee7a38c85c63223079dc9d17a290ed089` with a clean tree after that commit; the historical redacted audit recorded 12 code-pattern findings in earlier history. Re-run `git status --ignored` and confirm `backend/.env`, `backend/.env.local`, and `backend/.env.release_v1` are ignored. Do not force-add environment files.
4. **Complete live provider verification** with real Google OAuth, SMTP, Meta WhatsApp, and real-user OpenAI BYOK credentials. None was available here; none is claimed.
5. **Confirm the published Vercel backend** `dpl_CRo9kXq4CBL8p8oSaaAyKdSjNVoM` and its single daily cron remain as recorded, and verify hosted cron *invocation* / escalation effect with `ESCALATION_CRON_SECRET`. Only the schedule (`0 0 * * *`) is verified; the old hourly `0 * * * *` was invalid on Vercel Hobby.
6. **Netlify owner action:** confirm the deployed site and redeploy from GitHub `main` if needed. The public site returned HTTP 200 at `/` and `/api/health`, but the API returned 401 without a token, deploy ID `6b02db1360e3188d7f1074c6` could not be authenticated, and live Turbopack chunks differ from current main's webpack build — source sync is **NOT VERIFIED**. No redeploy was performed.
7. **Confirm database identity through operator-controlled means.** The `release-v1` read-only verification used the git-ignored `backend/.env.release_v1` file name only; Vercel withholds `DATABASE_URL` and Neon UI was unavailable. Do not claim direct Vercel-to-`.env` equality. The original production database was previously checked read-only and not modified; its state was not re-checked here.
8. **Prepare the container deployment plan** using the verified combined image `raphicsdigitalsolutions/smart-query-system:latest` / `:v1.0.0` (digest `sha256:2cf0a5dea54dffd643abf29a1fa7b72966899ff7235350b95fe1da793c9c2177`). The external Compose volume `smartquerysystem_smartquery_postgres_data` is host-specific and must never be deleted.
9. **Deploy/configure monitoring, retention, and malware scanning** if the original brief's clauses are enforced. Local disposable restore (PASS) and real ClamAV integration (`PASS_LOCAL_INTEGRATION_ONLY`) are complete, but `MALWARE_SCAN_ENABLED=false` by default, no hosted scanner is deployed, and hosted restore/monitoring/retention are NOT VERIFIED.
10. **Optional registry publication:** the current Docker Hub release is published and anonymously pull-verified. Publishing current changes to GHCR still requires `write:packages`; no GHCR registry content was changed.

## 9. Release gate checklist

All gates use explicit `PASS` / `PARTIAL` / `BLOCKED` / `NOT VERIFIED` dispositions backed by the
2026-11-24 final verification (`docs/TEST_REPORT.md` §10).

> **2026-11-24 Final Verification Update:** All 6 formerly open frontend dependency vulnerabilities were resolved (`next@16.4.6`, `zod@4.6.7`, `vitest@4.1.12`, `eslint-config-next@16.4.6`); `npm audit` and `npm audit --omit=dev` report **0 vulnerabilities**. Final reruns: backend **229 passed, 17 warnings in 410.30s (0:06:50)**, frontend typecheck/lint/Vitest (**3 passed**), Next.js 16 Webpack build (**PASS**, 12/12 pages), Playwright + axe (**12 passed in 2.0m**, no serious/critical violations), Compose configs and `docker build --check .` PASS, Alembic heads/current `feedf21773e1` with clean `alembic check`. The Vercel backend and Docker Hub image are published and verified, and the `release-v1` database was verified read-only. Only the daily cron *schedule* is verified. Formal institutional approval, live provider verification, hosted cron invocation, Netlify source sync, and operator secret review remain open.

| Gate | Status | Evidence / reason |
| --- | --- | --- |
| All code-level security remediation implemented and tested | **PASS** | `tests/test_release_hardening.py`, `tests/test_byok_rotation.py`, `tests/test_auth.py`, `tests/test_auth_audit.py` pass (`64 passed` focused run). |
| Full backend, frontend, Compose, and image-content verification | **PASS** | Final backend **229 passed, 17 warnings (410.30s)**; Playwright + axe E2E **12 passed (2.0m)**; Vitest **3 passed**; typecheck/lint/build (`12/12` pages, Next.js 16.4.6 webpack); both Compose `config --quiet` checks and `docker build --check .`; final combined image has no `.env`/key files (pattern matches are Next.js docs/library strings), non-root UID 10001. |
| No secret values printed or changed by the audit | **PASS** | Redacted SHA-256 fingerprints only (`docs/evidence/secret_audit.json`); no credential printed, rotated, or revoked. |
| Git repository state | **PASS** | release-evidence commit `2cb5595ee7a38c85c63223079dc9d17a290ed089` (`b51dd31` → `7ad663e` → `eb30f92` → `2cb5595`); clean working tree after the final commit. |
| Secret audit triage & credential rotation | **PARTIAL (triage PASS / rotation owner-action)** | Triage complete (385 tracked, 17 workspace potential, 12 history potential, 453 image potential, 4 current-local matches); rotation/revocation requires owner approval and was not performed. |
| BYOK encryption & rotation readiness | **PARTIAL (local PASS / prod rotation owner-action)** | Per-user Fernet encryption, cross-user isolation, and `rotate_byok_encryption_key.py` dry-run/commit CLI verified locally; live operator rotation requires owner approval. |
| Backup/restore rehearsal (disposable DB) | **PASS (local) / NOT VERIFIED (hosted)** | Rehearsal on disposable `postgres:16-alpine` returned `PASS` with matching hashes, stale row `1->0`, container removed, `production_touched: false`; hosted restore policy/execution not verified. |
| Malware scan integration | **PARTIAL (`PASS_LOCAL_INTEGRATION_ONLY`)** | ClamAV `1.5.5/28191` container verified clean `OK` (exit 0) and EICAR `FOUND` (exit 1); fail-closed hook tests pass; `MALWARE_SCAN_ENABLED=false` by default and no hosted scanner was deployed or verified. |
| Escalation cron readiness (FR-07) | **PARTIAL (local PASS + live schedule PASS / invocation NOT VERIFIED)** | Secret-protected sweep endpoint passes tests; final schedule is the valid daily `0 0 * * *` (Vercel Hobby permits at most once/day; hourly `0 * * * *` was invalid), current main matches deployed config, and `vercel crons ls` shows exactly that one cron. Hosted invocation and escalation effect NOT VERIFIED. |
| Frontend Playwright + axe E2E & unit tests | **PASS** | **12 passed in 2.0m** Playwright + axe (no serious/critical violations); Vitest **3 passed**. |
| Dependency audit (`npm audit`) | **PASS (0 vulnerabilities)** | `npm audit` and `npm audit --omit=dev` both report 0 vulnerabilities (`docs/evidence/npm_audit_final_2026-11-24.json`, `npm_audit_prod_final_2026-11-24.json`). |
| Vercel backend deployment | **PASS** | `dpl_CRo9kXq4CBL8p8oSaaAyKdSjNVoM` READY (production, CLI source), live backend smoke 200/200/200/401 as expected; deployment metadata names `b51dd31` with a dirty CLI working tree. |
| Netlify frontend deployment | **PARTIAL (public HTTP PASS / sync NOT VERIFIED)** | `/` and `/api/health` HTTP 200 (`Server: Netlify`); no token, API 401, deploy ID `6b02db1360e3188d7f1074c6` unconfirmed, live Turbopack chunks vs main's webpack. Owner must confirm/redeploy; no redeploy performed. |
| `release-v1` database isolation | **PASS (read-only)** | `neondb`, URL `sha256_12 5d1fc726d19b`, host `141f6064ec7f`, Alembic `feedf21773e1`, 17 tables, `departments=4`, `users=0`, `tickets=0`, `writes_performed=false`; branch identity from git-ignored `.env.release_v1` filename only; no Vercel-to-`.env` equality or old production DB state claimed. |
| Docker Hub publication | **PASS** | `latest` and `v1.0.0` both `sha256:2cf0a5dea54dffd643abf29a1fa7b72966899ff7235350b95fe1da793c9c2177`; anonymous pull (empty config) exit 0 and manifest HTTP 200. |
| GHCR publication | **PARTIAL (historical read-only PASS / new push BLOCKED)** | Historical GHCR existence/pull check used a different digest; publishing current changes requires `write:packages`. No GHCR registry content was changed. |
| Live provider verification (Google, SMTP, Meta, OpenAI BYOK) | **NOT VERIFIED** | Requires external production credentials and provider registration. |
| Original VU scope & public deployment governance | **FORMAL APPROVAL PENDING** | Requires signed supervisor/university scope-deviation approval and formal production-release sign-off; none is on file. |

**Final: TECHNICAL RELEASE COMPLETE; FORMAL APPROVAL PENDING — LIVE DEMONSTRATION; FORMAL SIGN-OFF NOT VERIFIED.**

No credential change, database write, Netlify redeploy, provider registration, or database volume deletion was performed.

Operator-facing detail: `docs/FINAL_RELEASE_BLOCKERS.md`, `docs/OPERATOR_ACTION_CHECKLIST.md`, and final evidence in `docs/TEST_REPORT.md` §10.
