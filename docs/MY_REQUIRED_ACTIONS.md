# My Required Actions & External Operator Tasks

**Project:** Smart Query Routing & Email Automation System  
**Document Date:** 2026-11-23; reconciled 2026-11-24  
**Purpose:** Concise checklist of only the tasks that genuinely require the project owner, university supervisor, or an authorized deployment operator with external account access.  
**Current status:** Technical release artifacts are published and verified; formal institutional/governance approval and live provider verification remain open. Authoritative evidence: `docs/evidence/phase5_live_verification_2026-11-24.json`. Current verdict: **TECHNICAL RELEASE COMPLETE; FORMAL APPROVAL PENDING**. Some task descriptions below are historical; completed items are marked as such.  
**Safety Rule:** Never paste real API keys, tokens, passwords, connection strings, or Fernet keys into chat, Git commits, or issue trackers.

---

## A. I Must Do (Project / Account Owner)

### A1. Review and Rotate Four Local Environment Credential Candidates
- **Required Account:** OpenAI Platform Dashboard, Vercel Account, Database Owner Console, and Local Host Workspace (`backend/.env`, `backend/.env.local`).
- **Exact Instructions:**
  1. Inspect the four local-only unignored environment matches identified by `scripts/secret_audit.py` (by SHA-256 12-char fingerprint only):
     - `OPENAI_API_KEY` (`backend/.env:42`, fingerprint `089ee82c29af`)
     - `BYOK_ENCRYPTION_KEY` (`backend/.env:51`, fingerprint `f70b8084e710`)
     - `VERCEL_OIDC_TOKEN` (`backend/.env.local:2`, fingerprint `3e0e10366f60`)
     - `DATABASE_URL` (`backend/.env:17`, fingerprint `c1271fe222ae`)
  2. Revoke or reissue `VERCEL_OIDC_TOKEN` and `OPENAI_API_KEY` in their provider consoles if they were ever shared or used outside local testing; keep global `OPENAI_API_KEY` empty in production (`ALLOW_GLOBAL_OPENAI_FALLBACK=false`).
  3. Rotate the database password in the database provider console if `DATABASE_URL` points to a shared/hosted database.
  4. Rotate `BYOK_ENCRYPTION_KEY` **only** using the staged re-encryption CLI in Task C1 below so existing encrypted user keys are not lost.
- **Risk:** Premature revocation of active credentials breaks live integrations; replacing `BYOK_ENCRYPTION_KEY` before running the re-encryption CLI makes stored personal keys unrecoverable.
- **Verification:** Re-run `python scripts/secret_audit.py`; confirm old provider keys show disabled in provider consoles and new fingerprints differ from the baseline four fingerprints.

### A2. Approve Semver-Major Frontend Dependency Upgrades (`npm audit`) — COMPLETED 2026-11-24
- **Status:** Done and verified — `vitest@4.1.12`, `zod@4.6.7`, `next@16.4.6`, `eslint-config-next@16.4.6`, `next build --webpack`; both audits report **0 vulnerabilities**. The commands below are historical reproduction steps; no further approval is needed for this item.
- **Required Account:** Repository Owner / Technical Lead approval (already obtained for the completed work).
- **Exact Instructions (historical):**
  1. Approve the major-version migration window for `next@16.4.6` (fixes nested `postcss@8.4.31`), `zod@4.6.7`, and `vitest@4.1.12` (fixes `@vitest/mocker` and `tinypool`).
  2. In `frontend-next/`, run:
     ```powershell
     npm install --save-dev vitest@4.1.12
     npm install zod@4.6.7
     npx next@canary upgrade --agent=latest
     npm install next@16.4.6
     ```
  3. Run `npm run typecheck`, `npm run lint`, `npm run test`, `npm run build`, and `npm run test:e2e`.
- **Risk:** Major version upgrades (`next` 15→16, `zod` 3→4, `vitest` 3→4) introduce breaking schema and framework API changes if applied without a dedicated regression review.
- **Verification:** `npm audit --json` and `npm audit --omit=dev --json` both report `0` vulnerabilities and all frontend/E2E tests pass.

### A3. Supply `write:packages` Token If Publishing Updated Images to GHCR
- **Required Account:** GitHub Account Owner (`raphicsdigitalsolutions`) with `write:packages` Personal Access Token.
- **Exact Instructions:**
  1. Note that `ghcr.io/raphicsdigitalsolutions/smart-query-system:latest` exists and is anonymously pullable at the historical digest `sha256:417e017081a460adfe310236e13b3e117cb972c11c5c93370968aa866a2b0f0f`; GHCR publication is still blocked. The current release image is on Docker Hub at `raphicsdigitalsolutions/smart-query-system:latest` / `:v1.0.0`, digest `sha256:2cf0a5dea54dffd643abf29a1fa7b72966899ff7235350b95fe1da793c9c2177`, matching local and anonymously pull-verified.
  2. When ready to publish a pinned release tag, authenticate locally:
     ```powershell
     docker login ghcr.io -u <github-username>
     docker build -t ghcr.io/raphicsdigitalsolutions/smart-query-backend:v1.0.1 ./backend
     docker push ghcr.io/raphicsdigitalsolutions/smart-query-backend:v1.0.1
     ```
- **Risk:** Pushing to `:latest` without a pinned version tag complicates rollback.
- **Verification:** `docker buildx imagetools inspect ghcr.io/raphicsdigitalsolutions/smart-query-backend:v1.0.1` returns HTTP 200 and a valid manifest digest in an unauthenticated session.

---

## B. University Must Approve (Supervisor / Institutional Governance)

### B1. Sign Off on Architectural & Tooling Substitutions vs. Original Brief
- **Required Account:** University Project Supervisor (`Saima Jamil`, `Saima.jamil@vu.edu.pk`).
- **Exact Instructions:**
  1. Present `docs/AUTHORITATIVE_COMPLETION_MATRIX.md` and `docs/FINAL_RELEASE_BLOCKERS.md` to the supervisor.
  2. Obtain written sign-off for the derived proposal's engineering substitutions relative to `AllProjectsS26.pdf`:
     - Per-user OpenAI BYOK + LangGraph instead of global free-tier Gemini/Claude keys (and acknowledgement that BYOK shifts token cost to the user supplying a key).
     - Native FastAPI services, SQLAlchemy/PostgreSQL tables, SMTP, and Meta Cloud API adapter instead of self-hosted n8n, Baileys, and Google Sheets.
     - Active leave-window routing exclusion and auto-reply (`InstructorLeave`) without a separate multi-stage leave-approval state machine.
  3. Record the signed approval date and reference in `docs/AUTHORITATIVE_COMPLETION_MATRIX.md`.
- **Risk:** Without signed supervisor approval, differences between the original brief and the derived proposal remain open governance blockers for formal grading/release sign-off.
- **Verification:** Signed supervisor confirmation attached or referenced in `docs/RELEASE_READINESS.md`.

### B2. Approve Data Retention, Deletion, and Public Exposure Policy
- **Required Account:** University Supervisor / Institutional Data Owner.
- **Exact Instructions:**
  1. Review the retention schedule in `docs/DEPLOYMENT_GUIDE.md` §13 (academic ticket retention period, notification log pruning window, encrypted off-host backup retention).
  2. Approve before loading real student records into any publicly reachable deployment.
- **Risk:** Processing real student queries without an approved retention and privacy policy violates institutional data governance (`D-SEC-04`).
- **Verification:** Written retention and public-deployment authorization recorded in `docs/RELEASE_READINESS.md`.

---

## C. Deployment Operator Must Do (For Production / Hosted Go-Live Only)

### C1. Execute Staged BYOK Fernet Key Rotation (When Rotating `BYOK_ENCRYPTION_KEY`)
- **Required Account:** Production Deployment Operator with PostgreSQL backup access and Secret Manager write access.
- **Exact Instructions:**
  1. Take a full PostgreSQL dump (`pg_dump -Fc`) and snapshot the attachment volume (`smartquerysystem_smartquery_attachments_data`).
  2. Generate a new Fernet key:
     `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
  3. From `backend/`, run the dry-run first, then commit only if all rows decrypt:
     ```powershell
     $env:BYOK_ROTATION_OLD_KEY = '<current-fernet-key>'
     $env:BYOK_ROTATION_NEW_KEY = '<new-fernet-key>'
     .\.venv\Scripts\python.exe -m app.cli.rotate_byok_encryption_key --dry-run
     .\.venv\Scripts\python.exe -m app.cli.rotate_byok_encryption_key --commit
     Remove-Item Env:BYOK_ROTATION_OLD_KEY, Env:BYOK_ROTATION_NEW_KEY
     ```
  4. Update `BYOK_ENCRYPTION_KEY` in the secret manager and restart the backend container.
- **Risk:** Updating `BYOK_ENCRYPTION_KEY` without running `--dry-run` and `--commit` first renders existing encrypted rows in `user_api_keys` undecryptable.
- **Verification:** CLI outputs `mode=commit rows=<N> changed=<N> committed=true` and existing users' `/api/v1/settings/api-key` status remains `configured`.

### C2. Configure and Verify Live External Providers (Google OAuth, SMTP, Meta WhatsApp, OpenAI BYOK)
- **Required Account:** Google Cloud Console owner, Domain DNS/SMTP administrator, Meta for Developers Business admin, and disposable test user with a personal OpenAI API key.
- **Exact Instructions:**
  1. **Google OAuth:** Create a Web OAuth 2.0 Client ID with authorized JavaScript origin `https://<your-domain>`, set `GOOGLE_OAUTH_ENABLED=true`, `GOOGLE_OAUTH_CLIENT_ID`, and `NEXT_PUBLIC_GOOGLE_CLIENT_ID`, and rebuild the frontend.
  2. **SMTP:** Configure a verified sender mailbox (`MAIL_FROM`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`) with SPF/DKIM/DMARC records.
  3. **Meta WhatsApp:** Set `WHATSAPP_ENABLED=true`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_VERIFY_TOKEN`, and `INTAKE_WEBHOOK_TOKEN`; register `https://<your-domain>/api/v1/integrations/whatsapp/webhook` in Meta.
  4. **BYOK Live Probe:** Sign in as a staff test account, add a personal OpenAI key in `/settings`, run one analysis on a disposable ticket, approve the draft, and delete the test key from `/settings`.
- **Risk:** Misconfigured origins or unverified sender domains cause provider rejections (`401`/`503`).
- **Verification:** `GET /api/v1/integrations/status` reports `true` for enabled providers, and live delivery/audit rows are captured without exposing tokens.

### C3. Verify Hosted FR-07 SLA Cron, Target-Host Backup Restore, and Deployed ClamAV Scanner
- **Required Account:** Hosting Platform Operator (Vercel / Container Host / Neon).
- **Exact Instructions:**
  1. Set `ESCALATION_CRON_SECRET` in the host secret manager and verify hosted invocation of the daily cron (`0 0 * * *`, `POST /api/v1/tickets/escalation/sweep` with `X-Cron-Secret`) escalates an overdue test ticket. The live cron list already shows one daily job; actual invocation is NOT VERIFIED. Hobby allows at most once/day.
  2. Run a backup/restore verification on a scratch database in the target hosting environment (`docs/OPERATOR_ACTION_CHECKLIST.md` §6).
  3. If attachment malware scanning is enforced in production, install ClamAV on the backend host and set `MALWARE_SCAN_ENABLED=true` and `MALWARE_SCAN_COMMAND="clamscan --no-summary {file}"`.
- **Risk:** Without `ESCALATION_CRON_SECRET`, the serverless sweep endpoint fails closed with `503 escalation_cron_not_configured`; enabling `MALWARE_SCAN_ENABLED=true` without a scanner binary fails closed with `503 attachment_scan_unavailable`.
- **Verification:** Host logs show HTTP `200` (`{"scanned":...,"escalated":...}`) on cron trigger, scratch restore hashes match, and EICAR upload returns `422 attachment_malware_detected`.

---

## D. Not Required for Local / University Demonstration

None of the items in Sections A, B, or C are required to run or present the complete local university demonstration on this machine:

1. **Live Google Cloud OAuth Client ID:** Not required locally — Argon2id email/password authentication and role isolation work offline across all 9 seeded accounts, and Google ID-token verification is verified offline by RSA test fixtures (`backend/tests/test_oauth.py`).
2. **Live SMTP Server or Meta WhatsApp Business Account:** Not required locally — in-app notifications, deduplication, template rendering, internal-note suppression, and token-gated inbound email/WhatsApp webhook adapters work locally and are verified by `test_notifications.py` and `test_integrations.py`.
3. **Paid OpenAI API Key:** Not required locally — `TKT-DEMO0001` is pre-seeded with a full grounded AI analysis (`KB-CS-101` citation, `94%` confidence) waiting at the Human Approval Gate so you can demonstrate `Approve & post reply` live in the browser at zero cost, while `TKT-DEMO0002` demonstrates the fail-closed BYOK guard (`402 ai_personal_key_required`).
4. **GHCR Package Push (`write:packages`):** Not required locally — local Dockerfiles and `scripts/start_local_demo.ps1` run entirely from the local checkout.
5. **Production Neon / Vercel / Netlify Access:** Not required and must not be connected during local demonstration — `backend/demo_server.py` uses an isolated disposable SQLite database (`frontend-next/.e2e/demo_local_test.db`).

---

## E. Release verification follow-ups (owner/operator, 2026-11-24)

Current verdict: **TECHNICAL RELEASE COMPLETE; FORMAL APPROVAL PENDING**. Authoritative evidence: `docs/evidence/phase5_live_verification_2026-11-24.json`.

- **Netlify source sync — NOT VERIFIED:** public root and `/api/health` returned HTTP 200, but no token was available and the API returned 401. Live HTML uses Turbopack chunks while current main builds with webpack after `75d6f16`; do not claim the live site matches main. Confirm/redeploy from GitHub main if needed. Deploy ID `6b02db1360e3188d7f1074c6` could not be authenticated. No redeploy was performed.
- **Vercel backend — verified:** deployment `dpl_CRo9kXq4CBL8p8oSaaAyKdSjNVoM` READY/production/source CLI; aliases `smart-query-backend.vercel.app` and `smart-query-backend-inforaphicsdigital-8444.vercel.app` (Vercel-login protected; public HTTP not verified); metadata commit `b51dd31` with dirty CLI tree but deployed config already contains the daily cron and current `origin/main` (`2cb5595`) matches.
- **release-v1 database — read-only:** `neondb`, URL fingerprint `5d1fc726d19b`, host fingerprint `141f6064ec7f`, Alembic `feedf21773e1`, 17 public tables, 4 departments, 0 users, 0 tickets, no writes. Branch identity from the operator-provided, git-ignored `backend/.env.release_v1` file name; hosted equality not verified. Original production database previously checked read-only and not modified; not re-checked here.
- **Still NOT VERIFIED:** Google OAuth, SMTP, Meta WhatsApp, real-user BYOK, hosted cron invocation, university approval, hosted restore/malware scanner, monitoring/retention.
