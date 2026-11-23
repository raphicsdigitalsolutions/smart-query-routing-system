# Final Release Blockers — Smart Query Routing System

**Document date:** 2026-11-23  
**Scope:** Local-only final release-blocker reconciliation. No commit, push, tag, branch, deployment,
registry write, production database access, billing change, or credential rotation/revocation was
performed.  
**Authority:** The original brief `C:\Users\user\Downloads\AllProjectsS26.pdf` remains authoritative.
The in-repo proposal PDF is a derived blueprint, not institutional approval.  
**Companion runbook:** `docs/OPERATOR_ACTION_CHECKLIST.md` contains operator-owned actions and exact
commands.

## 1. Verdict

| Target | Verdict | Basis |
| --- | --- | --- |
| Production / public release | **FAIL — DO NOT DEPLOY** | Four current-local credential candidates require owner review/rotation; live Google OAuth, SMTP, Meta WhatsApp, real-user BYOK, hosted FR-07 cron, production restore, deployed malware scanning, monitoring/retention and signed university approval are unverified; `npm audit` reports 6 vulnerable packages; publication of the current local changes to GHCR is blocked; original-brief deviations are unsigned. |
| Local / offline demonstration | **CONDITIONAL PASS** | Backend `225 passed, 17 warnings in 265.61s`; focused malware tests `10 passed`; Playwright + axe `11 passed` with no serious/critical violations; typecheck/lint/build, Compose config, image builds, disposable backup/restore rehearsal and redacted secret triage are complete. Use throwaway/local credentials only; do not expose publicly. |

The earlier live hackathon deployment on Netlify/Vercel/Neon is recorded in
`docs/HACKATHON_DEPLOYMENT_REPORT.md`. It did not close the governance FAIL or any signed-deviation
requirement.

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

## 3. Dependency blockers (`npm audit`)

Evidence: `docs/evidence/npm_audit_full_2026-11-23.json`,
`docs/evidence/npm_audit_prod_2026-11-23.json`,
`docs/evidence/npm_audit_summary.json` and
`docs/evidence/npm_dependency_paths_2026-11-23.txt`.

`npm audit` reports **6 vulnerable packages (2 moderate, 2 high, 2 critical)** across **10 unique
GHSA advisories**. `npm audit --omit=dev` reports 3 packages (`next`, `postcss`, `zod`); the critical
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
| Hosted FR-07 cron | Secret-protected sweep, hourly `backend/vercel.json`, deterministic escalation | `tests/test_escalation.py`, `tests/test_escalation_serverless.py`, E2E-ready endpoint | Hosted scheduler execution, `ESCALATION_CRON_SECRET` configured, observed overdue escalation/audit/notification in target host |
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
| Four current-local credential candidates reviewed/rotated by owner | FAIL — pending |
| BYOK re-encryption migration executed safely | FAIL — pending; plan ready |
| Dependency audit (`npm audit`) | FAIL — 6 vulnerable packages; fixes unapproved |
| Live provider verification (Google, SMTP, Meta, OpenAI BYOK) | FAIL — blocked |
| Hosted FR-07 cron | NOT VERIFIED |
| Production-equivalent restore and malware deployment | NOT VERIFIED |
| GHCR package existence / anonymous pull | PASS (read-only evidence) |
| GHCR publication of current local changes | BLOCKED — missing `write:packages` |
| Signed university scope/deviation approval | FAIL — pending |
| Public deployment approval and host plan | FAIL — pending |

**Final: FAIL for production/public release; CONDITIONAL PASS for local/offline demonstration only.**

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

## 8. Explicit non-actions

No commit, push, branch, tag, deployment, DNS/TLS change, provider registration, billing change,
GitHub remote change, registry write, production database access/modification, credential
rotation/revocation, or destructive working-tree change was performed while producing this document.
The E2E files remain untracked working-tree files; they are not described as committed.
