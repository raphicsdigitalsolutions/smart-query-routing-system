# Operator Action Checklist — Release Blockers

> **Current verified release status (2026-11-24):** Technical release artifacts are published and verified; formal institutional/governance approval and live provider verification remain open. Authoritative evidence: `docs/evidence/phase5_live_verification_2026-11-24.json`. Current verdict: **TECHNICAL RELEASE COMPLETE; FORMAL APPROVAL PENDING**. Historical FAIL wording below is superseded.

**Document date:** 2026-11-23; reconciled 2026-11-24  
**Audience:** System owner / deployment operator with approved credentials.  
**Decision context:** Open operator-owned items are formal scope/sign-off approval, live provider verification, hosted-restore/monitoring confirmation and Netlify source-sync confirmation. The earlier **FAIL — DO NOT DEPLOY** decision was a historical governance verdict, not the current status. This checklist is a runbook, not authorisation to perform the actions.  
**Safety rule:** Nothing in this checklist should paste a token, key, password, connection string or
secret value into chat, a ticket, a shell history file, a committed file, or a log. Use placeholders
such as `<operator-supplied value>` and read values only from the operator's secret manager or secure
shell environment.

## 0. Preconditions before any action

- [ ] Written owner approval for the specific action, change ID, maintenance window and rollback owner.
- [ ] Signed/university decision on scope deviations, zero-cost interpretation, leave workflow and public-release governance (blocker G below).
- [ ] For credential or key work: confirm whether rotation/revocation is authorised. It is **not** authorised by the 2026-11-23 audit.
- [ ] For production data work: fresh encrypted backup plus attachment-volume snapshot; verify the backup by restoring to a scratch target first.
- [ ] For registry work: GitHub credential with `write:packages` issued and stored locally by the owner; no token pasted into chat.
- [ ] For dependency work: explicit approval for semver-major Next.js/Zod and Vitest 4 toolchain changes.
- [ ] Confirm the target is not the existing production/external volume unless explicitly approved. Never delete `smartquerysystem_smartquery_postgres_data`.

Baseline state recorded by the 2026-11-23 audit (historical): `HEAD 6f388d03a680daf1e63466d65e30c62029aa892b`,
one local commit, `origin` configured, 39 modified tracked files and 47 untracked paths (including
the E2E suite). Current state: `origin/main` is
`2cb5595ee7a38c85c63223079dc9d17a290ed089` with a clean working tree; chain `b51dd31` → `7ad663e`
→ `eb30f92` → `2cb5595`. Re-check before and after every operator action:

```powershell
git status --short --branch
git rev-parse HEAD
git diff --check
```

## 1. Reproduce the read-only evidence (no secrets, no writes)

From the repository root:

```powershell
python scripts/secret_audit.py
docker buildx imagetools inspect ghcr.io/raphicsdigitalsolutions/smart-query-system:latest
docker images --digests --format '{{.Digest}}' ghcr.io/raphicsdigitalsolutions/smart-query-system:latest
```

From `frontend-next/`, capture fresh audits (use `cmd /c` so PowerShell does not rewrite the npm shim
output):

```powershell
cmd /c "npm audit --json > ..\docs\evidence\npm_audit_full_<DATE>.json"
cmd /c "npm audit --omit=dev --json > ..\docs\evidence\npm_audit_prod_<DATE>.json"
npm ls next postcss zod vitest @vitest/mocker tinypool
```

Historical baseline: 6 vulnerable packages (2 moderate, 2 high, 2 critical); production-only 3
(next/postcss/zod). Current expectation: **0 vulnerabilities** in both `npm audit` and
`npm audit --omit=dev` after the 2026-11-24 remediation. Historical GHCR digest baseline:
`sha256:417e017081a460adfe310236e13b3e117cb972c11c5c93370968aa866a2b0f0f`; current Docker Hub
image digest: `sha256:2cf0a5dea54dffd643abf29a1fa7b72966899ff7235350b95fe1da793c9c2177`.

## 2. Blockers A–B: credential candidates and BYOK migration

### A. Owner review of four fingerprint-only matches

Evidence: `docs/evidence/secret_audit.json`, `docs/SECRET_AUDIT_REMEDIATION_PLAN.md`.

- [ ] Review `OPENAI_API_KEY` (`089ee82c29af`), `BYOK_ENCRYPTION_KEY` (`f70b8084e710`),
      `VERCEL_OIDC_TOKEN` (`3e0e10366f60`) and `DATABASE_URL` (`c1271fe222ae`) by fingerprint only.
- [ ] Decide for each: still valid, already rotated elsewhere, shared inadvertently, or safe local-only value.
- [ ] If approved, rotate provider-issued values first (`VERCEL_OIDC_TOKEN`, `OPENAI_API_KEY`),
      then `DATABASE_URL` per database owner procedure, then the Fernet key using section B.
- [ ] Record the decision and evidence in the change log. Do **not** print old or new values.

**Risk:** premature revocation breaks live integrations; premature Fernet replacement makes stored
BYOK keys unrecoverable. **Verification:** provider console confirms old value disabled; audit
fingerprints change after rerunning `python scripts/secret_audit.py`.

### B. Safe BYOK Fernet re-encryption (approval required; not yet performed)

Prerequisites: owner approval, maintenance window, database backup, attachment-volume snapshot,
current and new Fernet keys in a secure operator shell/secret manager, and no application writes
during the window.

1. Back up the database and attachment volume (from repository root):

   ```powershell
   docker compose -f docker-compose.yml exec -T postgres pg_dump -U smartquery -d smartquery_db -Fc -f /tmp/smartquery_backup.dump
   docker compose -f docker-compose.yml cp postgres:/tmp/smartquery_backup.dump ./smartquery_backup.dump
   docker compose -f docker-compose.yml exec postgres rm -f /tmp/smartquery_backup.dump
   ```

   Store the dump encrypted off-host. Also snapshot `smartquerysystem_smartquery_attachments_data`
   and export the current `BYOK_ENCRYPTION_KEY` to approved secure storage.

2. Generate a new Fernet key using the command in `docs/DEPLOYMENT_GUIDE.md` §3. Keep it only in the
   secret manager / secure shell. Do not put it in `.env`, Git, chat, or command-line arguments.

3. From `backend/`, run the dry run (changes nothing):

   ```powershell
   $env:BYOK_ROTATION_OLD_KEY = '<operator-supplied current key>'
   $env:BYOK_ROTATION_NEW_KEY = '<operator-supplied new key>'
   .\.venv\Scripts\python.exe -m app.cli.rotate_byok_encryption_key --dry-run
   Remove-Item Env:BYOK_ROTATION_OLD_KEY, Env:BYOK_ROTATION_NEW_KEY
   ```

   Expected output is counts only, for example `mode=dry-run rows=<N> changed=0 committed=false`.
   Any non-zero exit means stop; no row was written.

4. Only if every row decrypts, commit:

   ```powershell
   $env:BYOK_ROTATION_OLD_KEY = '<operator-supplied current key>'
   $env:BYOK_ROTATION_NEW_KEY = '<operator-supplied new key>'
   .\.venv\Scripts\python.exe -m app.cli.rotate_byok_encryption_key --commit
   Remove-Item Env:BYOK_ROTATION_OLD_KEY, Env:BYOK_ROTATION_NEW_KEY
   ```

   Expected: `mode=commit rows=<N> changed=<N> committed=true`. The CLI verifies every row with the
   new key and rolls back on any failure.

5. Update `BYOK_ENCRYPTION_KEY` in the secret manager, then:

   ```powershell
   docker compose -f docker-compose.yml up -d --force-recreate backend
   docker compose -f docker-compose.yml exec backend python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).read().decode())"
   ```

6. Verify in the UI/API that an existing user's BYOK status is still `configured`, AI features still
   work with that user's own key, and no user had to re-enter a key. Re-run the focused BYOK tests:

   ```powershell
   .\.venv\Scripts\python.exe -m pytest -q tests/test_byok.py tests/test_byok_rotation.py
   ```

7. Only after verification, destroy the old key under the approved retention policy.

**Rollback:** if any row fails to decrypt, stop; the database is unchanged. If commit verification
fails, the CLI rolls back. If the configured key was changed prematurely, restore the previous
secret-manager value and the pre-rotation database backup before restarting the backend.
**Never** replace `BYOK_ENCRYPTION_KEY` before the dry run and commit verification succeed.

## 3. Blocker C: dependency remediation (approval required)

Reference: `docs/evidence/npm_audit_summary.json` and `docs/FINAL_RELEASE_BLOCKERS.md` §3.

- [ ] Approval recorded for Next.js 15→16, Zod 3→4 and Vitest 3→4 migrations.
- [ ] Re-capture the baseline audit (section 1) before changing anything.
- [ ] Apply the smallest safe changes from `frontend-next/`:

   ```powershell
   npm install --save-dev vitest@4.1.12
   npm install zod@4.6.7
   # Next.js requires the official upgrade/codemod review before installing:
   npx next@canary upgrade --agent=latest
   ```

   The upgrade helper is documented at
   `https://nextjs.org/docs/app/guides/upgrading/version-16`; it prepares the 15→16 migration and
   codemod. After reviewing its changes, install the pinned target with
   `npm install next@16.4.6`. If the operator does not use the upgrade CLI, follow the same guide
   manually.

- [ ] Verify lockfile resolution: `npm ls vitest @vitest/mocker tinypool next postcss zod eslint-config-next`.
      Expect `@vitest/mocker@4.1.12`, no vulnerable `tinypool@1.1.1`, `next@16.4.6` with nested
      `postcss@8.5.23`, `zod@4.6.7`, and `eslint-config-next` aligned with the Next.js major version.
- [ ] Re-run all checks from `frontend-next/`:

   ```powershell
   npm run typecheck
   npm run lint
   npm run build
   npm run test
   npm run test:e2e
   cmd /c "npm audit --json > ..\docs\evidence\npm_audit_full_after_<DATE>.json"
   cmd /c "npm audit --omit=dev --json > ..\docs\evidence\npm_audit_prod_after_<DATE>.json"
   ```

- [ ] Re-run the full backend suite from `backend/` after any BFF/schema change:
      `.\.venv\Scripts\python.exe -m pytest -q`.
- [ ] Record remaining findings, if any. Do not mark the dependency gate PASS until both audits are clean or
      each residual advisory has a written, time-bound exception.

**Risk:** breaking API/type changes in Zod 4, Next.js 16 routing/caching defaults, and Vitest 4 config
migration. Do not combine this step with deployment or registry publication.

## 4. Blocker D: live provider verification

Use disposable test accounts/records and the real provider values already configured by the owner.
No secret value is printed.

### D1. Google OAuth

Prerequisites: real Web-application OAuth client ID, registered JavaScript origin, frontend image
rebuilt with `NEXT_PUBLIC_GOOGLE_CLIENT_ID`, backend `GOOGLE_OAUTH_ENABLED=true`.

- [ ] Configure per `docs/DEPLOYMENT_GUIDE.md` §8, then rebuild/restart:

   ```powershell
   docker compose -f docker-compose.yml build frontend
   docker compose -f docker-compose.yml up -d
   ```

- [ ] Sign in with a real Google account in a browser; confirm role assignment, `user_oauth_accounts`
      linking, no privilege escalation, and a `auth.login_succeeded` audit event.
- [ ] Verify Google button is absent/fails closed when disabled or misconfigured.
- [ ] Evidence: redacted screenshots/API responses plus timestamp. Do not capture ID tokens.

### D2. SMTP

Prerequisites: real mailbox/app password, `MAIL_FROM` aligned with verified domain, SPF/DKIM/DMARC.

- [ ] Connectivity check (does not send mail):

   ```powershell
   docker compose -f docker-compose.yml exec backend python -c "import os,smtplib; s=smtplib.SMTP(os.environ['SMTP_HOST'], int(os.environ['SMTP_PORT']), timeout=10); s.starttls(); s.login(os.environ['SMTP_USER'], os.environ['SMTP_PASSWORD']); s.quit(); print('SMTP OK')"
   ```

- [ ] Create a disposable ticket and confirm the configured recipient receives the notification,
      the `notifications` row shows delivered status, and no internal note or unapproved AI draft
      was emailed. Clean up disposable records.

### D3. Meta WhatsApp

Prerequisites: real access token, phone number ID, verify token, webhook registered, approved recipient.

- [ ] Configure per `docs/DEPLOYMENT_GUIDE.md` §8 and verify the GET handshake with operator-held
      values (do not paste the verify token into shared logs):

   ```powershell
   curl.exe -fsS "https://<host>/api/v1/integrations/whatsapp/webhook?hub.mode=subscribe&hub.verify_token=<VERIFY_TOKEN>&hub.challenge=<CHALLENGE>"
   ```

- [ ] Send a real approved-recipient message; confirm outbound delivery and notification row.
- [ ] Send an inbound message through Meta; confirm `POST /api/v1/integrations/whatsapp/inbound`
      with `X-Intake-Token` creates a ticket with `channel=whatsapp`, is repeat-safe, and maps the
      correct student.

### D4. Real-user OpenAI BYOK

Prerequisites: a user supplies their own key directly through the UI; global `OPENAI_API_KEY` remains
empty and `ALLOW_GLOBAL_OPENAI_FALLBACK=false`.

- [ ] In the UI, add and validate the user's personal key; confirm status shows `configured` and no
      key material appears in responses, logs or browser storage.
- [ ] Run one low-cost real AI request; confirm token/cost metadata where the provider supplies it,
      approval gating for drafts, and per-user rate limiting.
- [ ] Delete/disable the test key afterwards and confirm AI features fail closed with
      `402 ai_personal_key_required`. No billing change or global key was introduced.

## 5. Blocker E: hosted FR-07 cron

Prerequisites: deployed host, `ESCALATION_CRON_SECRET` configured in the host secret store, scheduler
enabled, approval for live escalation of test tickets.

- [ ] Confirm the host has `ESCALATION_CRON_SECRET` set and cron configured (final daily
      `0 0 * * *` in `backend/vercel.json` for Vercel-style hosting; Hobby allows at most once/day).
      The live cron list already shows exactly that one job; **actual invocation is NOT VERIFIED**.
- [ ] Create a disposable overdue ticket in a non-production dataset, or use an approved test window.
- [ ] Observe the scheduled run in host logs; or, with explicit approval, trigger once:

   ```powershell
   curl.exe -X POST -H "X-Cron-Secret: <host secret>" -fsS https://<host>/api/v1/tickets/escalation/sweep
   ```

- [ ] Verify `escalated_at`, audit rows and notifications; confirm repeat runs do not duplicate them.
      Remove disposable records. A local `tests/test_escalation_serverless.py` pass is not live evidence.

**Risk:** real tickets can be escalated and real notifications sent. Do not run against production
data without a maintenance window and owner approval.

## 6. Blocker F: production backup/restore, malware scanning and monitoring

### F1. Backup / restore

- [ ] Run the backup commands from `docs/DEPLOYMENT_GUIDE.md` §9 on the target host.
- [ ] Restore to a **scratch** database first; verify schema/record hashes and stale-row cleanup.
      The local baseline is schema `ed7d1ab744886956c3e35ddde4674a05b01da26ef8313199b2c741e35917664b`
      and records `00e07e9f6182a27c59db5e2b9b0d51055011c13029485c4647b9ba4cc994d419`, but a hosted
      restore must produce its own evidence.
- [ ] Include the attachment volume snapshot in the same restore test. Never delete or recreate the
      existing database volume as a shortcut.
- [ ] Record retention/owner sign-off. A disposable local rehearsal PASS is not production evidence.

### F2. Deployed malware scanning

- [ ] Deploy/configure ClamAV or an equivalent scanner on the target host.
- [ ] Set `MALWARE_SCAN_ENABLED=true`, `MALWARE_SCAN_COMMAND="clamscan --no-summary {file}"` and
      `MALWARE_SCAN_TIMEOUT_SECONDS=20` (or approved equivalents); recreate the backend.
- [ ] Verify fail-closed behavior: clean upload succeeds; EICAR fixture returns `422
      attachment_malware_detected`; missing scanner returns `503 attachment_scan_unavailable`.
- [ ] Keep `MALWARE_SCAN_ENABLED=false` only if the owner formally accepts the risk and documents it.

### F3. Monitoring and retention

- [ ] Configure health/metrics/alerts, log retention, backup retention and deletion policy per
      `docs/DEPLOYMENT_GUIDE.md` §13; attach written university/data-owner approval.

## 7. Blocker G: university and release governance

- [ ] Obtain signed approval for the OpenAI/BYOK substitution versus Gemini/Claude, FastAPI/local DB
      versus n8n/Baileys/Sheets/Supabase/Render, zero-cost interpretation, leave workflow, FR-07
      automation, hosted deployment topology and public release.
- [ ] Confirm the in-repo proposal PDF is a derived blueprint, not institutional approval.
- [ ] Update `docs/AUTHORITATIVE_COMPLETION_MATRIX.md`, `docs/MASTER_REQUIREMENTS_CHECKLIST.md` and
      `docs/RELEASE_READINESS.md` with the signed decision and change ID.
- [ ] Do not treat the hackathon deployment or the GHCR package as approval.

## 8. Blocker H: GHCR publication (only after approval and write access)

Historical GHCR fact (2026-11-23): `ghcr.io/raphicsdigitalsolutions/smart-query-system:latest` exists,
is anonymously pullable and matches digest `sha256:417e017081a460adfe310236e13b3e117cb972c11c5c93370968aa866a2b0f0f`.
The then-current local changes were not published to GHCR and no push was attempted. The current
release image is published on Docker Hub at digest
`sha256:2cf0a5dea54dffd643abf29a1fa7b72966899ff7235350b95fe1da793c9c2177` (§9); GHCR publication
remains BLOCKED pending `write:packages`.

- [ ] Owner supplies a local `write:packages` credential; never paste it into chat.
- [ ] Pin a release tag (not `latest`) and confirm which package name(s) are in scope.
- [ ] From the repository root, after explicit publication approval:

   ```powershell
   docker login ghcr.io -u <owner>
   docker tag smartquery-backend:phase7 ghcr.io/raphicsdigitalsolutions/<package>:<tag>
   docker push ghcr.io/raphicsdigitalsolutions/<package>:<tag>
   docker buildx imagetools inspect ghcr.io/raphicsdigitalsolutions/<package>:<tag>
   ```

- [ ] Set the agreed visibility, then verify anonymous pull without credentials in a clean session.
- [ ] Record the new digest. Do not report an image URL before manifest and anonymous pull verification.

## 9. Final release gate re-check

- [ ] Re-run section 1 evidence capture and attach fresh files.
- [ ] Re-run the full local suites: backend `pytest`, frontend typecheck/lint/build/Vitest/Playwright+axe,
      Compose config, image builds, redacted secret audit.
- [ ] Confirm all blockers A–H are either PASS with evidence or formally accepted with signed exceptions.
- [ ] Update `docs/FINAL_RELEASE_BLOCKERS.md`, `docs/RELEASE_READINESS.md` and the completion matrix.
- [ ] Only then obtain formal institutional approval. Current verdict: **TECHNICAL RELEASE
      COMPLETE; FORMAL APPROVAL PENDING** (the earlier FAIL is historical).
- [ ] Confirm the Netlify production deploy for `smart-query-routing-system.netlify.app` and redeploy
      from GitHub main if the live site still serves Turbopack chunks; no redeploy was performed
      during verification. Deploy ID `6b02db1360e3188d7f1074c6` is unconfirmed.
- [ ] If database parity matters, re-check `release-v1` against the hosted database: read-only
      verification found `neondb`, URL fingerprint `5d1fc726d19b`, host fingerprint
      `141f6064ec7f`, Alembic `feedf21773e1`, 17 public tables, 4 departments, 0 users, 0 tickets,
      no writes. Branch identity came from the git-ignored `backend/.env.release_v1` file name;
      hosted equality is NOT VERIFIED. Original production database previously checked read-only and
      not modified; its state was not re-checked here.

## 10. Explicit non-actions of the 2026-11-23 audit

No commit, push, branch, tag, deployment, registry write, DNS/TLS change, provider registration,
billing change, GitHub remote change, production database modification, credential
rotation/revocation, or destructive working-tree change was performed. The original production
database had been checked read-only earlier and was not modified. The Playwright/axe E2E files
were untracked working-tree files at that time; they are now committed on current `origin/main`
(`2cb5595`), as noted in §9.
