# Deployment Guide — Smart Query Routing System

Provider-independent production packaging and operations guide for the Docker Compose stack.

> **Historical scope note:** This guide was originally authored as provider-independent packaging and operations documentation; no public deployment was performed at that time.
>
> **Deployment addendum (2026-11-22):** A real public deployment was subsequently executed: FastAPI on Vercel Hobby, Next.js BFF on Netlify Free, and Neon PostgreSQL. The live topology, exact URLs, deploy IDs, verification results, serverless deviations, and unresolved gates are recorded in `docs/HACKATHON_DEPLOYMENT_REPORT.md`. The guidance below remains the operational reference for reproduction, rollback, and provider setup.
>
> **Current verified release status (2026-11-24):** Technical release artifacts are published and verified; formal institutional/governance approval and live provider verification remain open. Authoritative evidence: `docs/evidence/phase5_live_verification_2026-11-24.json`. Current verdict: **TECHNICAL RELEASE COMPLETE; FORMAL APPROVAL PENDING**.

## 1. What is deployed

| Service | Image / build | Exposure | Health |
| --- | --- | --- | --- |
| `postgres` | `postgres:16` | No host port; internal only | `pg_isready` |
| `backend` | `./backend/Dockerfile` → `smartquery-backend:${IMAGE_TAG}` | Internal `8000` only; optional loopback debug port | `GET /health` |
| `frontend` | `./frontend-next/Dockerfile` → `smartquery-frontend:${IMAGE_TAG}` | `0.0.0.0:${FRONTEND_PORT:-3000}` | `GET /api/health` (proxies backend) |

- Compose project name: `smartquerysystem` (set explicitly in `docker-compose.yml`).
- Internal bridge network: `smartquerysystem_internal`. It is "internal" in the sense that only the frontend is published; outbound internet remains available for SMTP, OpenAI, Meta, and Google.
- Backend entrypoint applies Alembic migrations (`alembic upgrade head`) before starting uvicorn. Current head revision: `feedf21773e1` (Phase 7 platform capabilities). Chain: `44273a775ed8` → `47ebce833eae` → `b7d4e91c2a83` → `feedf21773e1`.
- Both application images run as non-root users (`app` UID 10001, `nextjs` UID 10001).
- No secret is baked into either image. `backend/.env` and `frontend-next/.env*` are excluded by `.dockerignore`.

### Data safety / existing database

Observed read-only before writing this guide:

```
docker volume ls
# local  smartquerysystem_smartquery_postgres_data

docker compose -f docker-compose.db.yml config
# volume source smartquery_postgres_data
# final name smartquerysystem_smartquery_postgres_data
# project name smartquerysystem
```

`docker-compose.yml` therefore declares the volume as **external** with the exact name:

```yaml
volumes:
  smartquery_postgres_data:
    name: smartquerysystem_smartquery_postgres_data
    external: true
```

Rules:

- `docker-compose.db.yml` is preserved unchanged and remains a local-DB-only helper.
- The first production `up` re-creates the existing `smartquery-postgres` container so it joins `smartquerysystem_internal` and no longer publishes `5432`. **The data volume is untouched.**
- Stop the DB-only stack first with `docker compose -f docker-compose.db.yml down` (no `-v`).
- **Never** run `docker compose down -v`, `docker volume rm`, or a volume-pruning command on this project. Never delete database records to "fix" a deployment.

## 2. Prerequisites

- Docker Engine 24+ with Compose v2 (validated here with Docker Compose v5.6.1).
- A domain name you control and a reverse proxy with HTTPS (Caddy/nginx/Traefik or a cloud load balancer).
- Provider accounts only for features you enable: SMTP provider, Google Cloud OAuth client, Meta WhatsApp Cloud API, OpenAI account for BYOK users.
- A backup of `smartquerysystem_smartquery_postgres_data` before any migration, restore, or rollback (see §9).

## 3. Environment setup

```powershell
Copy-Item .env.example .env
# Edit .env. Replace every REPLACE_WITH_* value. Never commit .env.
```

Generate values (Python 3.11+ with `cryptography` installed, e.g. the backend virtualenv):

```powershell
# Fernet key for BYOK_ENCRYPTION_KEY (exact required command)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# JWT signing secret
python -c "import secrets; print(secrets.token_urlsafe(48))"

# DATABASE password
python -c "import secrets; print(secrets.token_urlsafe(24))"

# INTAKE_WEBHOOK_TOKEN and WHATSAPP_VERIFY_TOKEN (generate two different values)
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Production requirements enforced by the backend settings validator:

| Variable | Requirement |
| --- | --- |
| `ENVIRONMENT` | `production` |
| `DEBUG` | Must be `false`; the backend fails startup if enabled in production |
| `JWT_SECRET_KEY` | Long, high-entropy, non-placeholder value; example/test values are rejected by fingerprint and pattern checks |
| `BYOK_ENCRYPTION_KEY` | Valid, non-placeholder Fernet key; example/test values are rejected |
| `JWT_ALGORITHM` | Must be `HS256` |
| `ALLOW_GLOBAL_OPENAI_FALLBACK` | Must be `false` (startup fails otherwise) |
| `OPENAI_API_KEY` | Leave empty under the production BYOK policy |
| `DATABASE_URL` | PostgreSQL URL; non-placeholder credentials; host `postgres` allowed for the internal Compose network, external hosts require `sslmode=require`, `verify-ca`, or `verify-full` |
| `BACKEND_CORS_ORIGINS` | Real HTTPS origins only; wildcard, localhost, and placeholder origins are rejected |
| `MAIL_FROM` | Real verified sender domain when `EMAIL_NOTIFICATIONS_ENABLED=true`; example domains are rejected |
| `GOOGLE_OAUTH_CLIENT_ID` | Required when `GOOGLE_OAUTH_ENABLED=true`; placeholder values are rejected |
| `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_VERIFY_TOKEN` | Required when `WHATSAPP_ENABLED=true`; placeholder values are rejected |
| `INTAKE_WEBHOOK_TOKEN` | Leave empty when unused; if set, must not be a placeholder |
| `NEXT_PUBLIC_API_BASE_URL` | Your real public HTTPS origin; rebuild frontend after change |
| `API_BASE_URL` | `http://backend:8000/api/v1` (server-side only) |

Startup validation is fail-closed and does not include secret values in error messages. It applies only when `ENVIRONMENT=production`; local development defaults remain usable.

Ticket attachments are written to `ATTACHMENT_STORAGE_DIR` (default `/app/var/attachments` in Compose) on the persistent `smartquerysystem_smartquery_attachments_data` volume. The database stores metadata and checksums only. Keep this volume in the same backup/restore window as PostgreSQL.

If a DB password contains URL-reserved characters, percent-encode it before putting it in `DATABASE_URL` (`urllib.parse.quote_plus`), or generate an alphanumeric-only password.

`NEXT_PUBLIC_*` variables are public by design and compiled into browser JavaScript. **Never** place JWT, database, SMTP, Meta, or OpenAI secrets in them.

## 4. Build and start

Validate configuration first (both must exit 0):

```powershell
docker compose -f docker-compose.db.yml config
docker compose -f docker-compose.yml config
```

Build and start (pin a tag so rollback is predictable):

```powershell
$env:IMAGE_TAG = "v1.0.0"        # PowerShell
# export IMAGE_TAG=v1.0.0        # bash/macOS/Linux

docker compose -f docker-compose.db.yml down   # no -v; preserves data
docker compose -f docker-compose.yml build
docker compose -f docker-compose.yml up -d
```

Notes:

- `NEXT_PUBLIC_API_BASE_URL` and `NEXT_PUBLIC_GOOGLE_CLIENT_ID` are passed as Docker **build args** by Compose. Changing them requires `docker compose build frontend`.
- `API_BASE_URL` is a runtime variable used only by the Next.js server (BFF), so changing it only needs `up -d`.
- The frontend image uses the standard `next start` production server because `next.config.ts` does not set `output: 'standalone'`. The package script's localhost bind is overridden with `--hostname 0.0.0.0` in the image CMD.
- Do not expose `8000` publicly. If needed for local debugging, uncomment the loopback-only `ports` entry in `docker-compose.yml` and never open it in a firewall/security group.

## 5. Migrations

Automatic (default): the backend entrypoint runs `alembic upgrade head` on every start before uvicorn. Alembic is idempotent — re-running at head is a no-op.

Verify:

```powershell
docker compose -f docker-compose.yml exec backend alembic current
docker compose -f docker-compose.yml exec backend alembic heads
# Expected head: feedf21773e1 (head)
```

Scaled deployments: run migrations once, then set `RUN_MIGRATIONS=false` for app replicas to avoid concurrent upgrades:

```powershell
$env:RUN_MIGRATIONS = "false"
docker compose -f docker-compose.yml run --rm backend alembic upgrade head
# Then deploy replicas with RUN_MIGRATIONS=false in .env/secret manager.
```

Planned downgrade (destructive for Phase 7 data — back up first):

```powershell
docker compose -f docker-compose.yml exec backend alembic downgrade b7d4e91c2a83
docker compose -f docker-compose.yml exec backend alembic current
```

## 6. Health checks and troubleshooting

```powershell
docker compose -f docker-compose.yml ps
docker compose -f docker-compose.yml logs -f backend frontend postgres

# Frontend health (public)
curl.exe -fsS http://localhost:3000/api/health

# Backend liveness (from inside the network)
docker compose -f docker-compose.yml exec backend python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).read().decode())"

# Database readiness
docker compose -f docker-compose.yml exec postgres pg_isready -U smartquery -d smartquery_db
```

Readiness endpoint for DB-dependent checks: `GET /api/v1/status/database` (HTTP 503 when unavailable). Interactive API docs: `/docs` (should be restricted or disabled at the edge if not needed publicly).

Common failures:

| Symptom | Likely cause |
| --- | --- |
| Backend exits immediately | Strict production validation rejected a placeholder/weak secret, invalid Fernet key, unsafe `DEBUG`, global fallback, placeholder DB credentials, localhost/external DB without TLS, wildcard/localhost CORS, or placeholder provider identity. Error text names the failing setting but never its value. |
| Backend cannot connect to DB | `DATABASE_URL` still points at `localhost`, or password differs from the initialized volume credentials |
| Frontend unhealthy but backend healthy | `API_BASE_URL` wrong; BFF `/api/health` cannot reach backend |
| Google button absent | `GOOGLE_OAUTH_ENABLED=false`, missing client ID, or frontend built without the client ID |
| AI panel says no personal key | Expected under BYOK; user must add a personal OpenAI key |

## 7. Domain, HTTPS, and reverse proxy

Set `NEXT_PUBLIC_API_BASE_URL=https://<your-domain>/api/v1` before building the frontend image. Terminate TLS at the proxy; cookies are `HttpOnly`, `SameSite=Lax`, and `Secure` in production.

Keep these paths on the frontend service: `/`, `/dashboard`, `/student`, `/staff`, `/hod`, `/admin`, `/api/auth/*`, `/api/backend/*`, `/api/health`.

Route backend-owned public paths (for example `/api/v1/integrations/email/inbound`, `/api/v1/integrations/whatsapp/inbound`, `/docs`, and `/api/v1/*`) to `backend:8000`. The Google credential exchange is a frontend BFF route (`POST /api/auth/google`) and must stay on `frontend:3000`. Verify the deployed `/openapi.json` before publishing provider URLs.

### Option A — Caddy (proxy as a container on `smartquerysystem_internal`)

```caddyfile
smartquery.example.edu {
  encode zstd gzip
  header {
    Strict-Transport-Security "max-age=31536000; includeSubDomains"
    X-Content-Type-Options "nosniff"
    Referrer-Policy "strict-origin-when-cross-origin"
  }

  handle /api/v1/* {
    reverse_proxy backend:8000
  }

  handle {
    reverse_proxy frontend:3000
  }
}
```

Attach the proxy container to the network created by this stack (`smartquerysystem_internal`); from another Compose project declare it as an external network with that exact name.

### Option B — nginx on the host (backend debug port on loopback only)

Uncomment the loopback `127.0.0.1:8000:8000` port in `docker-compose.yml`, then:

```nginx
server {
    listen 443 ssl http2;
    server_name smartquery.example.edu;

    ssl_certificate     /etc/letsencrypt/live/smartquery.example.edu/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/smartquery.example.edu/privkey.pem;

    location /api/v1/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Redirect HTTP→HTTPS and obtain certificates with your normal ACME tooling. Do not publish port 8000 in a firewall.

## 8. External provider configuration

### SMTP email

1. Create a dedicated mailbox/app password with your SMTP provider.
2. Set `SMTP_HOST`, `SMTP_PORT` (587 with STARTTLS), `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_USE_TLS=true`, `SMTP_USE_SSL=false`, `MAIL_FROM`, `EMAIL_NOTIFICATIONS_ENABLED=true`.
3. Align `MAIL_FROM` with your verified domain and publish SPF/DKIM/DMARC records.
4. Restart the backend: `docker compose -f docker-compose.yml up -d --force-recreate backend`.
5. Optional connectivity check (does not send mail):

```powershell
docker compose -f docker-compose.yml exec backend python -c "import os,smtplib; s=smtplib.SMTP(os.environ['SMTP_HOST'], int(os.environ['SMTP_PORT']), timeout=10); s.starttls(); s.login(os.environ['SMTP_USER'], os.environ['SMTP_PASSWORD']); s.quit(); print('SMTP OK')"
```

Notifications cover submission, assignment, public replies, escalation, and resolution. Internal notes and unapproved AI drafts are never emailed. Delivery failures must not break ticket operations. Live delivery was not verified here — it requires real provider credentials.

### Meta WhatsApp Cloud API

1. In Meta for Developers, create an app with the WhatsApp product, obtain the **Phone Number ID** and a system-user access token with `whatsapp_business_messaging` (and management scope if required by your setup).
2. Set `WHATSAPP_ENABLED=true`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_API_VERSION` (default `v21.0`), and a unique `WHATSAPP_VERIFY_TOKEN`.
3. In WhatsApp configuration → Webhook, set the callback URL to `https://smartquery.example.edu/api/v1/integrations/whatsapp/webhook` and the verify token to the same value as `WHATSAPP_VERIFY_TOKEN`, then subscribe to `messages`. The implemented GET handshake accepts Meta's `hub.mode=subscribe`, compares `hub.verify_token` with a constant-time check, and echoes `hub.challenge`; unconfigured or mismatched tokens fail closed with HTTP 401.
4. The implemented protected inbound-intake route is:
   `POST https://smartquery.example.edu/api/v1/integrations/whatsapp/inbound`
   It requires an `X-Intake-Token` header containing `INTAKE_WEBHOOK_TOKEN` and a JSON body with `student_email`, `body`, optional `department_id` and optional `auto_route`. The reverse proxy must forward `/api/v1/*` to `backend:8000`.
5. Set `INTAKE_WEBHOOK_TOKEN` as the server-side shared secret for protected inbound intake adapters. Never place it in the frontend or in a Meta URL where a header/secret can be used instead.
6. Live message delivery requires Meta approval, an approved recipient/phone number, and real tokens. None of that was performed here.

### Google OAuth2

1. In Google Cloud Console create an OAuth client of type **Web application**.
2. Authorized JavaScript origin: `https://smartquery.example.edu`.
3. Credential flow: this implementation uses Google Identity Services with a credential posted to the same-origin BFF route `POST /api/auth/google`; it does not use a redirect callback URI. Do not add a callback path unless you change the flow.
4. Set `GOOGLE_OAUTH_ENABLED=true`, `GOOGLE_OAUTH_CLIENT_ID`, and the identical `NEXT_PUBLIC_GOOGLE_CLIENT_ID`.
5. Rebuild the frontend image (public client ID is inlined) and restart the backend:

```powershell
docker compose -f docker-compose.yml build frontend
docker compose -f docker-compose.yml up -d
```

6. Google sign-in is optional. When it is disabled or misconfigured, email/password sign-in remains available (students self-register; staff/HOD/admin are provisioned by an administrator). Live OAuth verification requires the real client ID and was not performed.

## 9. Backup and restore

Back up before upgrades, migrations, restores, secret rotation, and rollbacks.

Backup (avoids shell text-encoding corruption of binary dumps):

```powershell
docker compose -f docker-compose.yml exec -T postgres pg_dump -U smartquery -d smartquery_db -Fc -f /tmp/smartquery_backup.dump
docker compose -f docker-compose.yml cp postgres:/tmp/smartquery_backup.dump ./smartquery_backup.dump
docker compose -f docker-compose.yml exec postgres rm -f /tmp/smartquery_backup.dump
```

Store the dump encrypted off-host and test restores regularly. A dump is a point-in-time copy; also retain volume-level snapshots where your platform supports them. A LOCAL VERIFIED rehearsal (`docs/evidence/backup_restore_rehearsal.json`, status `PASS`) used a disposable `postgres:16-alpine` container on `127.0.0.1:55432`; schema hash `ed7d1ab744886956c3e35ddde4674a05b01da26ef8313199b2c741e35917664b` and record hash `00e07e9f6182a27c59db5e2b9b0d51055011c13029485c4647b9ba4cc994d419` matched after clean restores, stale row count went 1 → 0, and the container was removed. This does not verify a hosted Neon restore and touched no production data.

Ticket attachment bytes are stored separately in `smartquerysystem_smartquery_attachments_data`; the database dump contains only their metadata and checksums. Back up that volume with an encrypted, point-in-time volume snapshot under the same schedule, and restore it together with the matching database dump. A database-only restore leaves attachment rows without their files.

Restore to a scratch database first (non-destructive verification):

```powershell
docker compose -f docker-compose.yml cp ./smartquery_backup.dump postgres:/tmp/smartquery_restore.dump
docker compose -f docker-compose.yml exec postgres createdb -U smartquery smartquery_restore_test
docker compose -f docker-compose.yml exec postgres pg_restore -U smartquery -d smartquery_restore_test /tmp/smartquery_restore.dump
docker compose -f docker-compose.yml exec postgres dropdb -U smartquery smartquery_restore_test
```

Full restore (destructive to current rows — stop app writers first):

```powershell
docker compose -f docker-compose.yml stop backend frontend
docker compose -f docker-compose.yml cp ./smartquery_backup.dump postgres:/tmp/smartquery_restore.dump
docker compose -f docker-compose.yml exec postgres pg_restore --clean --if-exists -U smartquery -d smartquery_db /tmp/smartquery_restore.dump
docker compose -f docker-compose.yml exec postgres rm -f /tmp/smartquery_restore.dump
docker compose -f docker-compose.yml start backend frontend
```

`--clean --if-exists` drops existing objects before recreating them. Never delete the volume as a shortcut.

## 10. Rollback

### Application image rollback

Keep previous image tags. With a previous `IMAGE_TAG` in `.env` (or shell):

```powershell
$env:IMAGE_TAG = "v1.0.0"   # previously built, known-good tag
docker compose -f docker-compose.yml up -d --no-build
```

Do not rebuild during rollback. If the failed release also applied a migration that the older image does not understand, downgrade the schema first (§5) after confirming compatibility from a backup/scratch restore.

### Migration rollback

```powershell
docker compose -f docker-compose.yml exec backend alembic downgrade b7d4e91c2a83
```

Phase 7 tables/data may be dropped by this downgrade. Verify with `alembic current`, then restart app services. Re-upgrade with `alembic upgrade head` when ready.

## 11. Secret rotation

| Secret | Rotation effect | Procedure |
| --- | --- | --- |
| `JWT_SECRET_KEY` | All sessions invalidated; users sign in again | Generate new value, update secret store/.env, `docker compose up -d --force-recreate backend` |
| `BYOK_ENCRYPTION_KEY` | Existing stored personal keys cannot be decrypted until re-encrypted | Use the staged dry-run/commit CLI below. Do not replace the configured key until every row decrypts and the commit verification succeeds |
| `POSTGRES_PASSWORD` | Existing cluster does **not** change from env alone | Run `ALTER USER smartquery WITH PASSWORD '<new>';` in PostgreSQL, then update `POSTGRES_PASSWORD` **and** `DATABASE_URL`, recreate backend |
| SMTP password | Mail delivery interrupted until updated | Rotate at provider, update value, recreate backend, revoke old app password |
| `WHATSAPP_ACCESS_TOKEN` | Outbound/inbound WhatsApp fails until updated | Rotate in Meta, update value, recreate backend, revoke old token |
| `WHATSAPP_VERIFY_TOKEN` / `INTAKE_WEBHOOK_TOKEN` | Webhook verification fails | Update provider configuration and env together, recreate backend |
| `GOOGLE_OAUTH_CLIENT_ID` | OAuth fails if mismatched | Update in Google Console + both env vars; rebuild frontend; revoke old client |

Always back up before rotation and verify health afterwards (§6).

### 11.1 Safe BYOK Fernet key rotation

The rotation CLI reads both keys from environment variables only. It never accepts keys as command-line arguments and never prints key material. It reads rows in one pass, decrypts every row with the old key before writing anything, re-encrypts in a single transaction, verifies every row with the new key, and rolls back on any failure. Row IDs, owners, providers, hints, validity flags, timestamps, and all other database records are preserved.

Procedure (operator-supplied credentials; maintenance window recommended):

1. Back up PostgreSQL **and** the existing secret-manager value of `BYOK_ENCRYPTION_KEY`. Do not delete database volumes.
2. Generate a new Fernet key with the command in §3. Keep the current key and new key only in the secret manager or a secure operator shell environment.
3. From `backend/`, run a dry run. This decrypts every stored BYOK row with the old key and changes nothing:

   ```powershell
   $env:BYOK_ROTATION_OLD_KEY = '<operator-supplied current key>'
   $env:BYOK_ROTATION_NEW_KEY = '<operator-supplied new key>'
   .\.venv\Scripts\python.exe -m app.cli.rotate_byok_encryption_key --dry-run
   Remove-Item Env:BYOK_ROTATION_OLD_KEY, Env:BYOK_ROTATION_NEW_KEY
   ```

   The output contains only counts (`mode`, `rows`, `changed`, `committed`). If any row cannot be decrypted, the command exits non-zero and no write is attempted.
4. If and only if the dry run succeeds, run the commit step:

   ```powershell
   $env:BYOK_ROTATION_OLD_KEY = '<operator-supplied current key>'
   $env:BYOK_ROTATION_NEW_KEY = '<operator-supplied new key>'
   .\.venv\Scripts\python.exe -m app.cli.rotate_byok_encryption_key --commit
   Remove-Item Env:BYOK_ROTATION_OLD_KEY, Env:BYOK_ROTATION_NEW_KEY
   ```

5. Verify the commit counts and application health, then update `BYOK_ENCRYPTION_KEY` in the secret manager and recreate/restart the backend. Confirm that a user's BYOK status still shows `configured` and that no previously stored key needs to be re-entered.
6. Only after verification, securely destroy the old key. Keep the backup until the retention window closes.

**Never** replace `BYOK_ENCRYPTION_KEY` before the dry run and commit verification succeed: doing so makes existing encrypted records unrecoverable without the old key. The CLI does not rotate the key in the secret manager by design.

## 12. BYOK policy and privacy

- Production requires `BYOK_ENCRYPTION_KEY` and forbids `ALLOW_GLOBAL_OPENAI_FALLBACK=true`. The global `OPENAI_API_KEY` stays empty.
- Each user adds a personal OpenAI key in their account settings. It is encrypted at rest, scoped to that user, never returned to the browser, never logged, and never shared with another account. Only a status hint (configured/not configured) is exposed.
- If a user has not configured a key, AI features fail closed with a clear message. Approval is still required before any AI draft is published.
- BYOK shifts API cost to the user/provider. It does **not** make the platform free; any "zero-cost tooling" claim remains unmet.
- Using Google, SMTP, Meta, or OpenAI sends the minimum necessary data to those external providers and is subject to their terms. Provider setup is honest and optional; no live provider integration was performed here.

## 13. Retention and deletion policy

No production records were deleted during Phase 7. Before accepting real university data, the deployment owner must set and enforce a written retention schedule. The application does not implement automatic purging.

| Data class | Minimum rule before go-live |
| --- | --- |
| Tickets, messages, attachments, AI drafts and audit history | Retain for the university's academic records period; do not delete ad hoc. Use scoped, authorised, logged deletion only where policy requires it. |
| Personal OpenAI keys | Stored encrypted in `user_api_keys`; delete immediately with the account or on user request. Rotation requires users to re-add keys unless an explicit re-encryption migration is provided. |
| Notification delivery rows | Retain long enough to prove delivery and support disputes; then prune under the approved retention schedule. |
| Database backups and volume snapshots | Encrypt off-host, restrict access, and retain according to the same schedule as the source records. Test restores before go-live. |
| Logs | Do not log secrets, raw keys, internal notes, or ticket bodies. Retain operational logs only as long as needed for incident response. |

Any manual deletion must be preceded by a backup and recorded in the change/incident log. Never use volume deletion as a data-cleanup method.

## 14. Validation performed for this packaging work

Exact commands and results:

| Command | Result |
| --- | --- |
| `docker volume ls` | Exit 0; showed `local smartquerysystem_smartquery_postgres_data` |
| `docker compose -f docker-compose.db.yml config` | Exit 0; unchanged local-DB config; volume name `smartquerysystem_smartquery_postgres_data` |
| `docker compose -f docker-compose.yml config` | Exit 0; 3 services (`postgres`, `backend`, `frontend`), network `smartquerysystem_internal`, external volume `smartquerysystem_smartquery_postgres_data`, and attachment volume `smartquerysystem_smartquery_attachments_data` |
| `docker compose -f docker-compose.yml config --quiet` | Exit 0 after adding the attachment volume and environment variable |
| `docker build -t smartquery-backend:phase7 ./backend` | Exit 0; final source tree tagged as `smartquery-backend:phase7` |
| `docker build -t smartquery-frontend:phase7 ./frontend-next` | Exit 0 after fixing a container-smoke-detected runtime TypeScript packaging defect |
| Isolated backend/frontend/PostgreSQL container smoke | All health checks passed; migration head applied; DB revision survived a scratch PostgreSQL restart; scratch resources removed |

Not performed against the existing production data volume: `docker compose up`, migrations against that live database, volume deletion, provider registration, or any public deployment. Exact smoke commands and results are in `docs/TEST_REPORT.md`.

## 15. Post-deployment reconciliation (2026-11-23)

The notes below use only local evidence. They do not change any live provider resource, hosted
configuration, credential, registry content or production database row.

### Delivered and LOCAL VERIFIED

- **FR-04b / FR-13:** deterministic instructor auto-routing in `backend/app/services/instructor_routing.py`.
  Only active `staff` users in the resolved department are eligible; active `InstructorLeave` windows
  (exclusive end bound) exclude staff, HOD/admin users are never auto-assigned, and there is no
  approval workflow. Selection is least non-terminal workload, then lowercase name, then ID. Tests:
  `backend/tests/test_instructor_routing.py`. University approval of the leave workflow is still open.
- **FR-06:** conditional polling, not SSE/push. `GET /api/v1/tickets/{ticket_id}/updates` returns an
  ETag and HTTP 304 for unchanged snapshots; the frontend `useTicketStatusPolling` hook polls about
  every 15 seconds. E2E polling spec: `frontend-next/e2e/tickets.spec.ts`.
- **FR-07:** `POST /api/v1/tickets/escalation/sweep` requires `X-Cron-Secret` matching
  `ESCALATION_CRON_SECRET` (constant-time; fails closed when unconfigured). `backend/vercel.json`
  schedules the path daily at `0 0 * * *` (the live Vercel cron list shows exactly that one daily
  job). Tests: `backend/tests/test_escalation_serverless.py`. Schedule existence is verified;
  actual hosted invocation is **NOT VERIFIED**.
- **FR-14:** password registration/login success and failure audit events are written without
  passwords or secrets (`auth.registered`, `auth.login_succeeded`, `auth.login_failed`). Tests:
  `backend/tests/test_auth_audit.py`.
- **Token lifetime:** production default remains 60 minutes; only the test environment uses 1440
  minutes (`backend/tests/test_token_expiry.py`).
- **Playwright + axe E2E:** build passed (`12/12` pages with Next.js 16.4.6 webpack) and **12 tests passed (2.0m)**; Vitest passed (`3 passed`); no serious/critical axe violations on login, student workspace or ticket detail. This is local evidence, not a hosted run.
- **Backup/restore:** see §9 and `docs/evidence/backup_restore_rehearsal.json` (status `PASS`; run with `$env:DEBUG = 'false'` on hosts where `DEBUG` is set to a non-boolean environment string such as `release`).
- **Malware scanning:** `docs/evidence/malware_scan_verification.json` is
  `PASS_LOCAL_INTEGRATION_ONLY`. Real `clamav/clamav:stable` (digest
  `sha256:64e30c0bf976198024deb3dc6d5cfe2485fb969c0f73549ba0fdb364b9469614`) returned `OK`/exit 0
  for a clean file and `Eicar-Test-Signature FOUND`/exit 1 for an EICAR fixture, using in-container
  base64 fixtures; focused tests: 10 passed. `MALWARE_SCAN_ENABLED=false` by default and no scanner
  is configured in the hosted environment. A Windows mount fixture failed and is **not** claimed as
  passing. NOT DEPLOYED.

### Test evidence and open items

- Backend full suite earlier historical runs: 218 passed, 225 passed. **Final full backend suite: `229 passed, 17 warnings in 410.30s (0:06:50)`, 0 failed/errors**; focused security/auth/malware/cron run: `64 passed, 17 warnings in 27.06s`; focused escalation/notification run: `42 passed, 17 warnings in 70.95s`; the 17 warnings are pre-existing LangSmith deprecations. Historical suite results remain recorded in `docs/TEST_REPORT.md`.
- Secret audit (`docs/evidence/secret_audit.json`, `docs/SECRET_AUDIT_REMEDIATION_PLAN.md`): 307
  tracked files, 17 workspace potential secrets, 12 git-history potential secrets, 453 docker-image
  potential secrets and 4 matches against current local environment values. Findings are stored as
  redacted field names/lengths/fingerprints, not values. No rotation or revocation was authorized or
  performed by this work.
- After installing Playwright/axe, `npm audit` reported 6 vulnerabilities; on **2026-11-24**, all 6 were remediated cleanly (`vitest@4.1.12`, `zod@4.6.7`, `next@16.4.6`, `eslint-config-next@16.4.6` with `next build --webpack`), bringing both `npm audit` and `npm audit --omit=dev` to **0 vulnerabilities** and rebuilding all Docker images cleanly. Frontend checks: Vitest `3 passed`; lint/typecheck **PASS**; build **PASS** (Next.js 16.4.6, webpack, `12/12` pages); Playwright + axe `12 passed in 2.0m`. Compose configs and `docker build --check` PASS; Alembic head/current `feedf21773e1` with a clean `check`.
- A unified single-container Supervisor image (`Dockerfile`, `docker/supervisord.conf`, `docker/backend-start.sh`) is published publicly at `https://hub.docker.com/r/raphicsdigitalsolutions/smart-query-system` (`latest`, `v1.0.0`, digest **`sha256:2cf0a5dea54dffd643abf29a1fa7b72966899ff7235350b95fe1da793c9c2177`**, matching the local image; the older `sha256:e9ed708…` digest is stale). Anonymous pull was verified with a temporary empty Docker config (exit 0) and an anonymous manifest HTTP 200. Container smoke was healthy with UID 10001, Supervisor backend+frontend **RUNNING**, and 4 HTTP checks returning 200 using disposable SQLite and no external integrations. No `.env` or key files are present in the image.
- **Live provider state (2026-11-24):** Vercel backend deployment `dpl_CRo9kXq4CBL8p8oSaaAyKdSjNVoM` is **READY**, target `production`, source CLI, aliased at `smart-query-backend.vercel.app` and `smart-query-backend-inforaphicsdigital-8444.vercel.app` (Vercel-login protected; public HTTP not verified). Its metadata commit is `b51dd31` with a dirty CLI working tree, but the deployed config already contains the daily cron and current release-evidence commit (`2cb5595ee7a38c85c63223079dc9d17a290ed089`) matches. Live `/health`, `/api/v1/status` and `/api/v1/status/database` returned HTTP 200; `/api/v1/departments` returned HTTP 401 as expected for an unauthenticated request.
- **Netlify caveat:** public root and `/api/health` returned HTTP 200, but authenticated deploy state and source sync are **NOT VERIFIED** (no token; Netlify API 401). Live HTML uses Turbopack chunks while current main builds with webpack after commit `75d6f16`, so do **not** claim the live site matches current main. Deploy ID `6b02db1360e3188d7f1074c6` could not be authenticated or confirmed. **Owner action:** confirm/redeploy from GitHub main; no redeploy was performed.
- **release-v1 database (read-only):** database `neondb`, URL fingerprint `5d1fc726d19b`, host fingerprint `141f6064ec7f`, Alembic `feedf21773e1`, 17 public tables, 4 departments, 0 users, 0 tickets; no writes. The `release-v1` branch identity comes from the operator-provided, git-ignored `backend/.env.release_v1` file name; Vercel sensitive values were withheld and the Neon UI was unavailable, so direct equality with the Vercel-hosted database is **NOT VERIFIED**. The original production database was previously checked read-only and not modified; this release-v1 check did not re-check it.
- **LIVE/BLOCKED/NOT VERIFIED:** the daily cron schedule exists and is visible in the live cron list, but actual hosted invocation is NOT VERIFIED. GHCR publication remains BLOCKED (missing `write:packages`); registry content, including `ghcr.io/raphicsdigitalsolutions/smart-query-system:latest`, was left untouched. Live Google OAuth, SMTP, WhatsApp, real-user BYOK, university approval, hosted restore/malware scanner, monitoring and retention are NOT VERIFIED.
- University approval is still required for scope deviations, tool/model/hosting substitutions, the
  zero-cost interpretation, the leave workflow and release/public governance. Current verdict:
  **TECHNICAL RELEASE COMPLETE; FORMAL APPROVAL PENDING**.
