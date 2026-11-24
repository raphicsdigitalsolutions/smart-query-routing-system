# Secret Audit — Redacted Triage and Remediation Plan

**Audit date:** 2026-11-23  
**Evidence:** `docs/evidence/secret_audit.json`  
**Implementation:** `scripts/secret_audit.py`  
**Status:** **TRIAGE COMPLETE; ROTATION/REVOCATION NOT AUTHORIZED**

> This document intentionally records no secret values. The audit stores only field names, line
> numbers, classifications, value lengths and 12-character SHA-256 fingerprints. No credential was
> printed, copied, changed, rotated or revoked. Do not treat a fingerprint as a usable secret.

## 1. Scope and result

The audit covered tracked files, all local workspace files, all reachable Git history, and the three
local/remote container images listed in the evidence file.

| Metric | Count |
| --- | ---: |
| Tracked files scanned | 307 |
| All workspace findings | 105 |
| Workspace findings classified `potential_secret` | 16 |
| Git-history findings classified `potential_secret` | 12 |
| Container-image findings classified `potential_secret` | 453 |
| Fingerprints matching current local environment values | 4 |

### Interpretation

- The 12 Git-history findings are the same 12 code-pattern matches present in tracked workspace
  source files; they are not evidence that a deployed credential was committed.
- The container-image findings are overwhelmingly dependency or source-code identifier matches,
  mostly under Python site-packages and Node modules. The backend image also contains six app-owned
  source-code matches that correspond to those tracked code patterns.
- The four current-local matches are **unignored local environment files**, not tracked source.
  They are the only findings that require possible credential handling action.

### Classification

| Class | Findings | Meaning / action |
| --- | --- | --- |
| Actual-secret candidate (treat as real until owner review) | 4 current-local matches listed in §2 | No provider check was performed, so liveness is unconfirmed. Treat as actual for release purposes; rotate/revoke only with approval. |
| Test fixture | Synthetic keys/tokens in `backend/tests/conftest.py`, `backend/tests/test_byok.py`, E2E config, including `ACCESS_TOKEN_EXPIRE_MINUTES=1440` | Informational. Production default 60 minutes is asserted by `backend/tests/test_token_expiry.py`. |
| False positive / safe sample | `.env.example`, `backend/.env.example`, `JWT_SECRET_KEY`/`SMTP_PASSWORD` reference values, dependency/source identifiers in images | Placeholders are rejected by strict production validation; no credential action. |
| Historical credential pattern | 12 Git-history `potential_secret` findings in reachable commit `6f388d0` | Code-pattern matches only; no current-local value was found in history. Not evidence of a committed live credential. |
| Pattern-only bulk matches | Workspace 105 = 36 placeholder/reference + 16 potential + 53 short/unknown; image 453 potential | Identifier/heuristic matches. No current-local value matched any image. |

## 2. Findings requiring possible action

The following fingerprints match current local environment values. They are listed by field, source
and fingerprint only.

| Field | Source | Location | Fingerprint | Required action |
| --- | --- | --- | --- | --- |
| `DATABASE_URL` | `backend/.env` | line 17 | `c1271fe222ae` | Local database connection string. Do not rotate without owner approval. |
| `OPENAI_API_KEY` | `backend/.env` | line 42 | `089ee82c29af` | Treat as potentially compromised. Rotation/revocation requires explicit approval. |
| `BYOK_ENCRYPTION_KEY` | `backend/.env` | line 51 | `f70b8084e710` | Treat as potentially compromised. Rotation requires a re-encryption plan and explicit approval. |
| `VERCEL_OIDC_TOKEN` | `backend/.env.local` | line 2 | `3e0e10366f60` | Treat as potentially compromised. Reissue only through the provider with approval. |

`JWT_SECRET_KEY` in `backend/.env` and `backend/.env.example`, and
`SMTP_PASSWORD` in `backend/.env`, were reclassified as placeholder/reference values after
auditing the placeholder patterns. They are not included in the four current-local matches.

## 3. Tracked code-pattern matches

The remaining `potential_secret` workspace findings are field-name or literal-assignment patterns in
source and tests, not deployed credentials. Representative locations are:

- `backend/app/core/config.py` (settings field declarations and local key derivation)
- `backend/app/cli/provision_admin.py` (password prompt handling)
- `backend/app/agents/services/agent_service.py` and `llm_service.py` (BYOK parameter handling)
- `frontend-next/src/app/api/auth/login/route.ts`, `register/route.ts` and the registration page
- `backend/tests/test_oauth.py`, `backend/tests/test_release_hardening.py`

These should be handled by code review and, where useful, clearer placeholder naming or test-fixture
annotations. No value from these files may be changed as part of this task without a new approved
scope.

## 4. Container-image triage

- `smartquery-backend:release-audit`: 207 findings; six are app-owned source-code patterns, the
  remainder are third-party Python package identifiers.
- `smartquery-frontend:release-audit`: 22 findings, all under Node dependencies and npm/Corepack
  documentation.
- `ghcr.io/raphicsdigitalsolutions/smart-query-system:latest`: 224 findings, all dependency/source
  identifier matches; the image was not pushed, replaced or deleted.

No current local environment value matched any container-image finding.

## 5. Remediation plan (requires approval)

1. **No automatic rotation or revocation.** Preserve all credentials until the owner explicitly
   authorises rotation or revocation.
2. **Owner review of the four fingerprints above** to determine whether each local value was ever
   shared, copied into a deployed provider setting, or committed under a historical value.
3. **If approved**, rotate/revoke in this order: provider-issued `VERCEL_OIDC_TOKEN`, `OPENAI_API_KEY`,
   `DATABASE_URL`; then rotate `BYOK_ENCRYPTION_KEY` using the staged plan below.
4. **If approved**, purge historical Git material containing a confirmed live credential using a
   coordinated history rewrite, force-push and collaborator re-clone. Do not attempt this locally
   without approval because the GitHub remote is out of scope.
5. Keep `backend/.env` and `backend/.env.local` ignored; continue using `.env.example` placeholders.
   Never use `git add -f` on environment files.
6. Re-run `python scripts/secret_audit.py` after any approved remediation and compare fingerprints,
   not values.

### 5.1 BYOK backup, re-encryption and rollback (not executed)

Risk: replacing `BYOK_ENCRYPTION_KEY` before all stored rows are re-encrypted makes existing personal
keys unrecoverable. The CLI at `backend/app/cli/rotate_byok_encryption_key.py` reads keys only from
`BYOK_ROTATION_OLD_KEY` / `BYOK_ROTATION_NEW_KEY`, never from arguments, prints counts only, and:

- `--dry-run` decrypts every row with the old key and writes nothing;
- `--commit` decrypts all rows first, re-encrypts in one transaction, verifies with the new key, and
  rolls back on any failure;
- refuses empty/invalid/identical keys and aborts if any row cannot be decrypted.

Operator sequence (all values supplied locally by the owner from the secret manager):

1. Schedule a maintenance window; stop accepting new BYOK changes if required by the change policy.
2. Back up PostgreSQL and the attachment volume, and export the current secret-manager value of
   `BYOK_ENCRYPTION_KEY` to approved secure storage. From the repository root:

   ```powershell
   docker compose -f docker-compose.yml exec -T postgres pg_dump -U smartquery -d smartquery_db -Fc -f /tmp/smartquery_backup.dump
   docker compose -f docker-compose.yml cp postgres:/tmp/smartquery_backup.dump ./smartquery_backup.dump
   docker compose -f docker-compose.yml exec postgres rm -f /tmp/smartquery_backup.dump
   ```

3. Generate a new Fernet key with the command in `docs/DEPLOYMENT_GUIDE.md` §3. Keep it only in the
   secret manager or a temporary secure shell environment.
4. From `backend/`, dry-run, then clear the variables:

   ```powershell
   $env:BYOK_ROTATION_OLD_KEY = '<operator-supplied current key>'
   $env:BYOK_ROTATION_NEW_KEY = '<operator-supplied new key>'
   .\.venv\Scripts\python.exe -m app.cli.rotate_byok_encryption_key --dry-run
   Remove-Item Env:BYOK_ROTATION_OLD_KEY, Env:BYOK_ROTATION_NEW_KEY
   ```

   A non-zero exit means one or more rows could not be decrypted; stop with no database change.
5. Only if every row decrypts, commit:

   ```powershell
   $env:BYOK_ROTATION_OLD_KEY = '<operator-supplied current key>'
   $env:BYOK_ROTATION_NEW_KEY = '<operator-supplied new key>'
   .\.venv\Scripts\python.exe -m app.cli.rotate_byok_encryption_key --commit
   Remove-Item Env:BYOK_ROTATION_OLD_KEY, Env:BYOK_ROTATION_NEW_KEY
   ```

   Confirm `changed` equals `rows` and `committed=true`; no key material is printed.
6. Update `BYOK_ENCRYPTION_KEY` in the secret manager, recreate/restart the backend, verify user BYOK
   status is still `configured` and AI features work without re-entry. Then run
   `.\.venv\Scripts\python.exe -m pytest -q tests/test_byok.py tests/test_byok_rotation.py` from
   `backend/`.
7. Only after verification, destroy the old key under the retention policy. Keep the database backup
   until the retention window closes.

**Rollback:** a failed dry run leaves the database untouched; a failed commit verification is rolled
back by the CLI. If the configured key was changed prematurely, restore the previous secret-manager
value and the pre-rotation database backup before restarting. Do not delete volumes or keys as a
shortcut. Full operator detail is in `docs/OPERATOR_ACTION_CHECKLIST.md` §2B and
`docs/DEPLOYMENT_GUIDE.md` §11.1.

## 6. Explicit non-actions

- No GitHub remote, branch, commit, tag, push, deployment or container registry content was changed.
- No production database was modified; the original production database had been checked read-only earlier.
- No provider console, billing setting, API key, token, password or encryption key was changed.
- No secret value appears in this plan, the audit output, tests, or the final status report.
