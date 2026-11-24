# Final Release Blockers — Smart Query Routing System

> **Current verified release status (2026-11-24):** Technical release artifacts are published and verified; formal institutional/governance approval and live provider verification remain open. Authoritative evidence: `docs/evidence/phase5_live_verification_2026-11-24.json`. Current verdict: **TECHNICAL RELEASE COMPLETE; FORMAL APPROVAL PENDING**. The 2026-11-23 FAIL verdicts below are historical/superseded; §9 records the current disposition.

**Document date:** 2026-11-23; reconciled 2026-11-24  
**Scope (2026-11-23 reconciliation; current state in §9):** Local-only final release-blocker reconciliation. No commit, push, tag, branch, deployment,
registry write, production database access, billing change, or credential rotation/revocation was
performed at that time.  
**Authority:** The original brief `C:\Users\user\Downloads\AllProjectsS26.pdf` remains authoritative.
The in-repo proposal PDF is a derived blueprint, not institutional approval.  
**Companion runbook:** `docs/OPERATOR_ACTION_CHECKLIST.md` contains operator-owned actions and exact
commands.

## 1. Verdict

| Target | Verdict | Basis |
| --- | --- | --- |
| Production / public release | **TECHNICAL RELEASE COMPLETE; FORMAL APPROVAL PENDING** (historical FAIL superseded) | Technical artifacts are published and verified: `origin/main` `2cb5595`, Vercel deployment `dpl_CRo9kXq4CBL8p8oSaaAyKdSjNVoM` READY with the daily cron schedule, Docker Hub image anonymously pull-verified, 0 npm vulnerabilities. Still open: four local credential candidates requiring owner review/rotation; live Google OAuth, SMTP, Meta WhatsApp, real-user BYOK, hosted cron invocation, production restore, deployed malware scanning, monitoring/retention, Netlify source sync and signed university approval; GHCR publication remains blocked. |
| Local / offline demonstration | **PASS (CONDITIONAL on throwaway credentials)** | Backend `229 passed, 17 warnings in 410.30s`, 0 failed/errors; focused malware tests `10 passed`; Playwright + axe `12 passed in 2.0m` with no serious/critical violations; typecheck/lint/build (`12/12` pages), Compose config, `docker build --check`, image builds, disposable backup/restore rehearsal and redacted secret triage are complete. Use throwaway/local credentials only; do not expose publicly. |

The earlier live hackathon deployment on Netlify/Vercel/Neon is recorded in
`docs/HACKATHON_DEPLOYMENT_REPORT.md`, with the final 2026-11-24 state in §9 below and in
`docs/evidence/phase5_live_verification_2026-11-24.json`. It did not grant formal approval or close
any signed-deviation requirement.

## 2. Resolved contradiction: GHCR image existence and pullability

The earlier "image URL unavailable / remote manifests missing" wording is stale for one specific
package. A read-only investigation of
`ghcr.io/raphicsdigitalsolutions/smart-query-system:latest` returned:

| Check | Result |
| --- | --- |
| Anonymous `/v2/` challenge | `401` (expected) |
| Anonymous token request | `200`, token present; token value was not stored or printed |
| `GET /v2/.../manifests/latest` | `200`, `application/vnd.oci.image.index.v1+json` |
| `Docker-Content-Digest` | `sha256:417e017081a460adfe310236e13b3e117cb972c11c5c93370968aa866a2b0f0f` |
| `docker buildx imagetools inspect` digest | Same `sha256:417e...a2b0f0f` |
| Local cached image digest | Same `sha256:417e...a2b0f0f` |
| Child manifests / config / first-layer blobs | `200` for both children (`amd64` platform plus attestation manifest) |
| Registry writes / pushes | **None attempted** |

Evidence: `docs/evidence/ghcr_readonly_investigation.json`.

**Conclusion:** the package exists, is anonymously pullable, and the remote digest matches the
previously recorded digest. This does **not** mean the current local working-tree changes are
published, nor that separate `smart-query-backend` / `smart-query-frontend` packages exist.
Publication of new content remains **BLOCKED** by missing `write:packages`; no registry content was
changed.

## 3. Dependency blockers (`npm audit`) — historical, remediated 2026-11-24

The 6 vulnerabilities listed below were fully remediated (`vitest@4.1.12`, `zod@4.6.7`,
`next@16.4.6`, `eslint-config-next@16.4.6` with `next build --webpack`). Current evidence:
`docs/evidence/npm_audit_post_remediation.json` and `npm_audit_post_remediation_prod.json`;
both `npm audit` and `npm audit --omit=dev` report **0 vulnerabilities**. The inventory below is
retained for traceability only.

Evidence: `docs/evidence/npm_audit_full_2026-11-23.json`,
`docs/evidence/npm_audit_prod_2026-11-23.json`,
`docs/evidence/npm_audit_summary.json` and
`docs/evidence/npm_dependency_paths_2026-11-23.txt`.

At the 2026-11-23 audit, `npm audit` reported **6 vulnerable packages (2 moderate, 2 high, 2 critical)** across **10 unique
GHSA advisories**. `npm audit --omit=dev` reported 3 packages (`next`, `postcss`, `zod`); the critical
Vitest-family findings are dev-toolchain findings and are not installed in the production-only
Docker runner (`npm ci --omit=dev`), though dev dependencies are present in build stages.

| Package | Installed | Chain / scope | Severity | Advisories | Fix target and smallest safe remediation | Risk / status |
| --- | --- | --- | --- | --- | --- | --- |
| `next` | 15.5.29 | Direct; BFF/UI framework; brings nested `postcss@8.4.31` | moderate | via `postcss` | `next@16.4.6` (semver-major; pins `postcss@8.5.23`). Use official upgrade/codemod, then rebuild and rerun all checks. | Requires Node >=20.9.0 and breaking-change review. **Not applied.** |
| `postcss` | 8.4.31 | `next@15.5.29 -> node_modules/next/node_modules/postcss`; nested, not the root Tailwind/Vite `postcss@8.5.33` | high | GHSA-qx2v-qp2m-jg93, GHSA-6g55-p6wh-862q, GHSA-fxqj-rqcc-2cmp, GHSA-r28c-9q8g-f849 | Fixed by the same approved `next@16.4.6` upgrade; do not hand-edit the nested dependency. | XSS / source-map path disclosure in CSS processing. **Not applied.** |
| `zod` | 3.25.76 | Direct; request schemas in login/register/Google BFF routes | high | GHSA-mrhx-c7xc-m3w5 | `zod@4.6.7` (semver-major), then typecheck/lint/build/Vitest/Playwright. | Major validation API migration; no patched v3 line reported. **Not applied.** |
| `vitest` | 3.2.4 | Direct **dev** dependency | critical | GHSA-5xrq-8626-4rwp, GHSA-82fw-gwwq-j7x9 | `npm install --save-dev vitest@4.1.12`; verify transitive resolution. | Node `^20 \|\| ^22 \|\| >=24` (local v22.23.2 satisfies). **Not applied.** |
| `@vitest/mocker` | 3.2.4 | `vitest@3.2.4 -> node_modules/vitest/node_modules/@vitest/mocker`; dev | moderate | GHSA-82fw-gwwq-j7x9, GHSA-qxg6-89mg-rqv8 | Covered by `vitest@4.1.12`, which pins `@vitest/mocker@4.1.12`. | Test-only. **Not applied.** |
| `tinypool` | 1.1.1 | `vitest@3.2.4 -> node_modules/tinypool`; dev | critical | GHSA-5gmw-xhrv-c9v3, GHSA-85c8-ppgw-ccpr | Covered by the `vitest@4.1.12` upgrade; verify with `npm ls tinypool`. | Test-only; not in production-runner image. **Not applied.** |

No `npm audit fix`, dependency install, lockfile rewrite or major upgrade was executed in this
reconciliation. Formal approval is required before applying any of these changes.

## 4. Secret triage and BYOK key-migration blocker

Evidence: `docs/evidence/secret_audit.json`, `docs/SECRET_AUDIT_REMEDIATION_PLAN.md`,
`scripts/secret_audit.py`. No value was printed, copied, logged or changed.

### 4.1 Classification

| Class | Findings | Disposition |
| --- | --- | --- |
| Actual-secret candidate — treat as real until owner decides | 4 current-local environment matches: `OPENAI_API_KEY` fingerprint `089ee82c29af`, `BYOK_ENCRYPTION_KEY` `f70b8084e710`, `VERCEL_OIDC_TOKEN` `3e0e10366f60`, `DATABASE_URL` `c1271fe222ae` | Owner review required. No revocation/rotation was authorised or performed. These are fingerprint-only references, not values. |
| Test fixture | `backend/tests/conftest.py`, `backend/tests/test_byok.py`, E2E config; synthetic `ACCESS_TOKEN_EXPIRE_MINUTES=1440` | Informational; production default 60 minutes is asserted by `backend/tests/test_token_expiry.py`. |
| False positive / safe sample | `.env.example`, `backend/.env.example`, `JWT_SECRET_KEY` and `SMTP_PASSWORD` reference/placeholder values, dependency and source identifiers in images | Not credentials; strict production validation rejects placeholders. |
| Historical credential pattern | 12 Git-history `potential_secret` findings in reachable commit `6f388d0` | Code-pattern matches; **no current-local environment value was found in history**. Not evidence of a committed live credential. |
| Pattern-only bulk matches | Workspace `105` total = 36 placeholder/reference, 16 potential, 53 short/unknown; image `453` potential matches | Mostly dependency/source identifiers; no current-local value matched any image. |

### 4.2 BYOK backup / re-encryption / rollback plan (operator-only, not executed)

The CLI `backend/app/cli/rotate_byok_encryption_key.py` reads keys only from
`BYOK_ROTATION_OLD_KEY` and `BYOK_ROTATION_NEW_KEY`, never from arguments, and never prints key
material. `--dry-run` decrypts every row without writing; `--commit` decrypts all rows first,
re-encrypts in one transaction, verifies with the new key, and rolls back on failure.

Required sequence before touching the configured key:

1. Obtain written owner approval and schedule a maintenance window.
2. Back up PostgreSQL and the attachment volume; export the current secret-manager value of
   `BYOK_ENCRYPTION_KEY` to approved secure storage. Keep the old key until the retention window
   closes.
3. From `backend/`, set the two rotation environment variables in the operator shell only, run
   `--dry-run`, confirm counts, and clear the variables.
4. Only if every row decrypts, rerun with `--commit`, confirm `changed` equals `rows`, and clear the
   variables.
5. Update `BYOK_ENCRYPTION_KEY` in the secret manager, recreate/restart the backend, and verify a
   user's BYOK status is still `configured` without re-entering a key.
6. Rollback: if any row fails to decrypt or verification fails, the CLI leaves the database
   unchanged (rollback on commit failure). If the configured key was changed prematurely, restore
   the previous secret-manager value and the pre-rotation database backup before restarting.
   Do not delete volumes or keys.

Exact commands and prerequisites are in `docs/OPERATOR_ACTION_CHECKLIST.md` and
`docs/DEPLOYMENT_GUIDE.md` §11.1. **No rotation or revocation has been performed.**

## 5. Missing evidence: code vs local verification vs live verification

| Requirement | Code / config implemented | Local / offline verification | Live production evidence still missing |
| --- | --- | --- | --- |
| Google OAuth (FR-01) | GIS ID-token verification, account linking, BFF `POST /api/auth/google` | `tests/test_oauth.py`, role/auth tests, BFF tests | Real Google client ID, registered origin, live sign-in, audit event and account link |
| SMTP (FR-02/FR-08) | SMTP service, notification templates, retries/dedupe | Fake-provider tests, notification rows | Real mailbox/app password, verified `MAIL_FROM`, SPF/DKIM/DMARC, delivered message and `notifications` status |
| Meta WhatsApp (FR-02/FR-08) | Webhook GET handshake, token-gated inbound adapter, outbound sender | `tests/test_integrations.py`, `tests/test_notifications.py` | Real Meta token/phone ID/verify token, registered webhook, approved recipient, live send + inbound ticket |
| Real-user BYOK (FR-03/FR-05) | Fernet-encrypted per-user keys, validation endpoint, no global fallback | BYOK/AI tests, live-key opt-in guard, fail-closed 402 | User-supplied real key, live low-cost inference, token/cost metadata, safe removal afterwards |
| Hosted FR-07 cron | Secret-protected sweep, daily `0 0 * * *` `backend/vercel.json`, deterministic escalation | `tests/test_escalation.py`, `tests/test_escalation_serverless.py`, E2E-ready endpoint; live cron list shows one daily job (schedule verified) | Actual hosted invocation, `ESCALATION_CRON_SECRET` state, observed overdue escalation/audit/notification in target host |
| Production backup/restore | `pg_dump`/`pg_restore` docs, attachment-volume backup guidance | Disposable rehearsal PASS with schema hash `ed7d1ab7...` and record hash `00e07e9f...`; stale row 1→0 | Host/provider-equivalent restore to scratch, retention/owner sign-off, no production restore performed |
| Deployed malware scanning | Optional fail-closed ClamAV hook | Real ClamAV local integration `PASS_LOCAL_INTEGRATION_ONLY`, 10 tests pass | Scanner deployed/configured on target host, `MALWARE_SCAN_ENABLED=true`, live clean/EICAR verification |
| Monitoring, retention, deletion policy | Health checks, audit logs, docs | Local health/audit checks | Monitoring provider, alerts, written retention/deletion approval, log review |
| University approval / governance | Original brief + derived proposal mapped in matrix | Document reconciliation only | Signed supervisor scope/deviation approval, zero-cost interpretation, leave workflow decision, public-release approval |
| Registry publication | Dockerfiles, Compose, local image builds | Existing `latest` package read-only pull/digest verified | `write:packages`, publication of current changes, pinned tag, anonymous pull of the new tag |

Local PASS never implies live provider, hosted scheduler, registry or governance approval.

## 6. Release gate status

| Gate | Status |
| --- | --- |
| Code-level security remediation implemented and locally tested | PASS |
| Full backend, frontend, Compose, image-content, E2E/axe verification | PASS (local) |
| Redacted secret triage complete; no values printed or changed | PASS |
| Four current-local credential candidates reviewed/rotated by owner | OPEN — owner review/rotation pending |
| BYOK re-encryption migration executed safely | OPEN — owner action pending; plan ready |
| Dependency audit (`npm audit`) | PASS — 0 vulnerabilities after 2026-11-24 remediation (historical FAIL superseded) |
| Live provider verification (Google, SMTP, Meta, OpenAI BYOK) | NOT VERIFIED — blocked without real credentials |
| Hosted FR-07 cron schedule | PASS (one daily job); invocation NOT VERIFIED |
| Production-equivalent restore and malware deployment | NOT VERIFIED |
| GHCR package existence / anonymous pull | PASS (read-only evidence) |
| GHCR publication of the release | BLOCKED — missing `write:packages` (Docker Hub publication PASS) |
| Signed university scope/deviation approval | OPEN — formal approval pending |
| Public deployment approval and host plan | OPEN — formal approval pending |

**Final: TECHNICAL RELEASE COMPLETE; FORMAL APPROVAL PENDING for production/public release; PASS (conditional on throwaway credentials) for local/offline demonstration.** The earlier FAIL is historical.

## 7. Evidence index

- `docs/OPERATOR_ACTION_CHECKLIST.md`
- `docs/evidence/ghcr_readonly_investigation.json`
- `docs/evidence/npm_audit_full_2026-11-23.json`
- `docs/evidence/npm_audit_prod_2026-11-23.json`
- `docs/evidence/npm_audit_summary.json`
- `docs/evidence/npm_dependency_paths_2026-11-23.txt`
- `docs/evidence/secret_audit.json`
- `docs/evidence/backup_restore_rehearsal.json`
- `docs/evidence/malware_scan_verification.json`
- `docs/RELEASE_READINESS.md`, `docs/AUTHORITATIVE_COMPLETION_MATRIX.md`,
  `docs/MASTER_REQUIREMENTS_CHECKLIST.md`, `docs/SECRET_AUDIT_REMEDIATION_PLAN.md`,
  `docs/TEST_REPORT.md`, `README.md`

## 8. Explicit non-actions of the 2026-11-23 reconciliation (historical)

No commit, push, branch, tag, deployment, DNS/TLS change, provider registration, billing change,
GitHub remote change, registry write, production database access/modification, credential
rotation/revocation, or destructive working-tree change was performed while producing this document.
The E2E files were untracked working-tree files at that time; they are now committed on current main
(see §9).

## 9. Final 2026-11-24 release state (current)

Authoritative evidence: `docs/evidence/phase5_live_verification_2026-11-24.json`. Current verdict: **TECHNICAL RELEASE COMPLETE; FORMAL APPROVAL PENDING**.

- **Git:** release-evidence commit `2cb5595ee7a38c85c63223079dc9d17a290ed089`; chain `b51dd31` → `7ad663e` (daily cron + Phase 1/2 evidence) → `eb30f92` (Docker Hub evidence) → `2cb5595` (live verification evidence); clean working tree after that commit.
- **Backend live:** Vercel `dpl_CRo9kXq4CBL8p8oSaaAyKdSjNVoM` READY/production/source CLI, aliases `smart-query-backend.vercel.app` and `smart-query-backend-inforaphicsdigital-8444.vercel.app`. Metadata commit `b51dd31` with dirty CLI working tree; deployed config already contains the daily cron and current main matches. Final schedule `0 0 * * *` for `/api/v1/tickets/escalation/sweep`; live cron list shows exactly that one job, but actual hosted invocation is NOT VERIFIED. Live `/health`, `/api/v1/status`, `/api/v1/status/database` HTTP 200; `/api/v1/departments` HTTP 401 expected.
- **Frontend live caveat:** Netlify public root and `/api/health` HTTP 200, but authenticated deploy state and source sync NOT VERIFIED (no token; API 401). Live HTML uses Turbopack chunks while current main builds with webpack after `75d6f16`; do not claim the live site matches current main. Deploy `6b02db1360e3188d7f1074c6` cannot be authenticated/confirmed. Owner action: confirm/redeploy from GitHub main. No redeploy was performed.
- **Database:** `release-v1` read-only — `neondb`, URL fingerprint `5d1fc726d19b`, host fingerprint `141f6064ec7f`, Alembic `feedf21773e1`, 17 public tables, 4 departments, 0 users, 0 tickets, no writes. Branch identity from the operator-provided, git-ignored `backend/.env.release_v1` file name; Vercel sensitive values withheld and Neon UI unavailable, so direct equality and old DB state are NOT VERIFIED.
- **Image:** Docker Hub `raphicsdigitalsolutions/smart-query-system:latest` / `:v1.0.0` digest `sha256:2cf0a5dea54dffd643abf29a1fa7b72966899ff7235350b95fe1da793c9c2177` matching the local image (old `sha256:e9ed708…` is stale). Anonymous pull with a temporary empty Docker config exit 0, anonymous manifest HTTP 200; container smoke healthy, UID 10001, Supervisor backend+frontend RUNNING, 4 HTTP checks 200 with disposable SQLite/no external integrations; no `.env` or key files in image.
- **Final verification:** backend 229 passed, 17 warnings in 410.30s (0 failed/errors); Vitest 3 passed; lint/typecheck PASS; build PASS (Next.js 16.4.6 webpack, 12/12 pages); Playwright + axe 12 passed in 2.0m; `npm audit` and `npm audit --omit=dev` 0 vulnerabilities; Compose configs and `docker build --check` PASS; Alembic head/current `feedf21773e1`, check clean.
- **NOT VERIFIED:** Google OAuth, SMTP, Meta WhatsApp, real-user BYOK, hosted cron invocation, university approval, hosted restore/malware scanner, monitoring/retention.
