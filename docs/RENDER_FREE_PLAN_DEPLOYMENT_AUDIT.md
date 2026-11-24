# Render FREE-Plan Deployment Audit — Smart Query Routing System

> **Historical analysis note:** This document records the 2026-11-22 Render Free-plan feasibility audit. Its FAIL verdicts are historical platform-fit findings, **not** the current release decision. The current verified release status is in `docs/evidence/phase5_live_verification_2026-11-24.json`: technical release artifacts are published and verified; formal institutional/governance approval and live provider verification remain open. Current verdict: **TECHNICAL RELEASE COMPLETE; FORMAL APPROVAL PENDING**.

**Date:** 2026-11-22  
**Revision:** Correction pass — accounts for the existing external Neon PostgreSQL project.  
**Scope:** Read-only audit of the current `main` branch (`6f388d0`) for deployment of the existing FastAPI backend to Render's Free web-service plan, using the already-created Neon PostgreSQL database. No deployment, push, credential change, database change, or GitHub modification was performed.

---

## Decision (read this first)

| Target | Verdict |
| --- | --- |
| **Production / public release (historical 2026-11-22 finding)** | **FAIL — DO NOT DEPLOY at the time of this audit** — superseded; see the historical analysis note above for current status |
| **Private, limited university demo on Render Free + Neon** | **CONDITIONAL PASS**, with accepted feature degradations listed in §11 |
| Local/offline demonstration | **CONDITIONAL PASS** (unchanged) |

**Correction to the previous revision:** the earlier "Free Postgres expires after 30 days" blocker is **withdrawn**. That limitation applies only to Render's own Free Postgres offering. This architecture uses an **external Neon PostgreSQL** project, so Render's 30-day expiry, 1 GB Render-Postgres cap and Render-Postgres backup limitations are **not applicable**.

Historical reasons this specific Render Free plan remained FAIL at the time of the audit are: Render Free's SMTP port block, ephemeral local disk for attachments, 15-minute spin-down (which breaks scheduled SLA escalation and adds ~1 minute wake latency), unverified 0.1 CPU / 512 MB headroom, and the then-unclosed release prerequisites (secret rotations, live provider verification, scope sign-off, deployment approval). The final deployment used Vercel + Netlify + Neon, not Render; see the historical analysis note above and current status in `docs/evidence/phase5_live_verification_2026-11-24.json`.

This audit does **not** override earlier release decisions:

| Prior decision | Status |
| --- | --- |
| Production/public release | **FAIL at the time of this 2026-11-22 audit** (historical; superseded by current verified status) |
| Local/offline demonstration | **CONDITIONAL PASS** (unchanged) |
| OpenAI BYOK only; no global production fallback | Retained |
| Both `frontend/` and `frontend-next/` retained | Retained |
| Existing Docker Compose path remains authoritative | Retained |
| Vercel may host only `frontend-next` | Retained |
| `C:\Users\user\Downloads\AllProjectsS26.pdf` is authoritative VU scope | Retained |

---

## 1. Files inspected

### Repository files

| File | What was verified |
| --- | --- |
| `backend/Dockerfile` | Build context, `COPY` paths, non-root user, `EXPOSE 8000`, `/health` Docker healthcheck, entrypoint runs `alembic upgrade head` unless `RUN_MIGRATIONS=false`, CMD `uvicorn app.main:app --host 0.0.0.0 --port 8000`. |
| `backend/.dockerignore` | Excludes `.env`, `.env.*`, local caches, `var/`, keys/certs — secret-safe build context. |
| `.dockerignore` | Root-context equivalent; confirms `./backend` is the intended build context. |
| `backend/requirements.txt` | Heavy dependency set: `uvicorn[standard]`, `psycopg[binary]>=3.1.18`, `langgraph==1.2.24`, `langchain-core==1.8.4`, `cryptography`, `pypdf`, `reportlab`, `openpyxl`, `httpx`, `pytest`. |
| `backend/app/main.py` | `/health` is a static liveness response with **no DB/provider check**; production-only SLA escalation asyncio task starts in `lifespan`; CORS from settings. |
| `backend/app/core/config.py` | Strict production validation (see §5); fails closed on placeholders, missing JWT/Fernet keys, non-PostgreSQL/non-TLS DB, unsafe flags. |
| `backend/app/db/session.py` | `create_engine(..., pool_pre_ping=True, pool_size=DB_POOL_SIZE, max_overflow=DB_MAX_OVERFLOW, pool_timeout=DB_POOL_TIMEOUT)` — synchronous psycopg 3 engine. `pool_pre_ping` is important for Neon scale-to-zero. |
| `backend/alembic/env.py` | Uses the **same** `settings.DATABASE_URL` as the app, with `poolclass=pool.NullPool` for the migration connection. |
| `backend/app/services/attachments.py` | Attachment bytes written to local filesystem via `Path.write_bytes`; only metadata/checksum stored in PostgreSQL. No storage-provider abstraction. |
| `backend/app/api/routes/tickets.py` | Attachment endpoints are **upload** and **list metadata only** — there is no endpoint that returns stored bytes. |
| `backend/app/services/email.py` | SMTP transport via `smtplib`; `send_email(...)` and `is_configured()` are the only integration seams. |
| `backend/app/services/notifications.py` | Calls `email_service.is_configured()` then `email_service.send_email(...)`; failures are recorded as `failed` notification rows and never raised. |
| `backend/app/services/whatsapp.py` | Separate HTTPS-based provider with its own `is_configured()`. |
| `backend/app/services/escalation.py` | Deterministic 24-hour SLA sweep, invoked only by the in-process async worker. |
| `docker-compose.yml` | Authoritative topology: backend context `./backend`, named volume `smartquery_attachments_data` at `/app/var/attachments`, external Postgres volume, `RUN_MIGRATIONS=true` default, full env-var contract. |
| `backend/.env.example`, `.env.example` | Env-var inventory and secret-placement policy. |
| `docs/RELEASE_READINESS.md` | Historical source of the 2026-11-22 production FAIL / local CONDITIONAL PASS decisions (superseded by the current status above). |
| `docs/CLOUDFLARE_ZERO_BUDGET_FEASIBILITY.md` | Prior completed audit; left unchanged. |
| Git state | `origin` = `https://github.com/raphicsdigitalsolutions/smart-query-routing-system.git`; branch `main` at `6f388d0`. |

### Official documentation consulted

**Render:** [Free](https://render.com/docs/free), [Compute plans](https://render.com/docs/compute-plans), [Web services](https://render.com/docs/web-services), [Health checks](https://render.com/docs/health-checks), [Docker](https://render.com/docs/docker), [Disks](https://render.com/docs/disks), [Blueprint spec](https://render.com/docs/blueprint-spec), [Monorepo support](https://render.com/docs/monorepo-support).

**Neon:** [Plans and Free limits](https://neon.com/docs/introduction/plans), [Connection pooling](https://neon.com/docs/connect/connection-pooling), [Connect from any app / connection strings](https://neon.com/docs/connect/connect-from-any-app), [Scale to zero](https://neon.com/docs/introduction/scale-to-zero).

**Drivers/providers:** [psycopg 3 prepared statements and PgBouncer](https://www.psycopg.org/psycopg3/docs/advanced/prepare.html), [Cloudflare R2 pricing](https://developers.cloudflare.com/r2/pricing/), [R2 S3 API compatibility](https://developers.cloudflare.com/r2/api/s3/api/), [Resend pricing](https://resend.com/pricing).

---

## 2. Files modified / created

| File | Action | Reason |
| --- | --- | --- |
| `docs/RENDER_FREE_PLAN_DEPLOYMENT_AUDIT.md` | **Updated (this correction pass)** | Replaces the withdrawn Render-Free-Postgres blocker with the Neon architecture, adds Neon pooling/SSL/driver analysis, HTTPS email and R2 assessment, SLA spin-down behaviour, resource risk, and a feature-by-feature verdict. |
| `render.yaml` | Created in the earlier pass; **unchanged in this pass** | Still an accurate minimal Blueprint; no correction required. Contains no secrets. Uses `autoDeployTrigger: 'off'` and omits `rootDir` so Root Directory stays blank. |

**Not changed:** application logic, dependencies, database schema/migrations, frontend(s), `Dockerfile`, `docker-compose.yml`, any `.env` file, or the prior Cloudflare report.

**Not performed:** no commit, push, deploy, GitHub change, secret generation, credential rotation, or database change. No secret values appear in either file.

---

## 3. Exact Render Dashboard settings

Use **Web Service** created from the Git repo (not a prebuilt image).

| Setting | Value | Verification / note |
| --- | --- | --- |
| Service type | **Web Service** | Required for HTTP traffic and HTTP health checks. |
| Repository | `raphicsdigitalsolutions/smart-query-routing-system` | Existing `origin`. |
| Branch | **`main`** | Matches current branch. |
| Root Directory | **blank** (repo root) | Repo root is required so `./backend` paths resolve. `rootDir` omitted from Blueprint. |
| Language / Runtime | **Docker** | Existing Dockerfile is authoritative. |
| Docker Build Context Directory | **`./backend`** | Matches `docker-compose.yml` `context: ./backend` and all `COPY` paths in the Dockerfile. |
| Dockerfile Path | **`./backend/Dockerfile`** | Relative to repo root. |
| Container Port | **`8000`** | The image binds `0.0.0.0:8000`. Render's documented mechanism is `PORT` (default `10000`); set `PORT=8000`. If the Dashboard exposes a **Container Port** field, set it to `8000`. Port 8000 is not reserved (`18012`, `18013`, `19099`). |
| Health Check Path | **`/health`** | Static HTTP 200 in `backend/app/main.py`. Render accepts 2xx/3xx within 5 s. |
| Plan | **Free — $0/month** | 0.1 CPU / 512 MB RAM. |
| Instances | **1** | Required; also the only supported count for any future attached disk. |
| Auto Deploy | **Disabled initially** | `autoDeployTrigger: 'off'`. |
| Region | **Singapore** (recommended) | Co-locates with the Neon project in AWS Asia Pacific 1 (Singapore), reducing latency across the ~1-minute wake path. Render supports `singapore`. |
| Persistent Disk | **Do not add on Free** | Not supported on Free; irrelevant while attachments remain on local disk. |
| Render Postgres | **Do not create** | Using external Neon; Render's Free Postgres limitations do not apply. |
| Start Command / Docker Command | **leave unset** | Use the Dockerfile `CMD`. |

---

## 4. Neon external PostgreSQL — connectivity, pooling, SSL, driver

**Known project details:** project `smart-query-routing-system`, region **AWS Asia Pacific 1 (Singapore)**, database **`neondb`**, connection pooling enabled.

### 4.1 Connectivity and SSL

- Neon speaks the standard PostgreSQL wire protocol on port **5432**; `postgresql+psycopg://` is supported by SQLAlchemy 2.x with `psycopg[binary]` (already a dependency).
- `sslmode=require` is present in Neon's supplied connection string and **also satisfies** the production validator in `backend/app/core/config.py`, which requires `sslmode=require|verify-ca|verify-full` for external hosts. Keep it. `channel_binding=require`, if present in the Neon string, is supported by psycopg 3 and can be kept.
- The Neon host is non-localhost and the driver backend is `postgresql`, so those validation checks pass.
- **Credential gotcha:** the validator rejects passwords containing any of `change|replace|your|example|placeholder|dummy|sample|test|dev|local|not-for-prod|not-secure|secret|password|admin` (case-insensitive) and requires ≥12 characters. A generated Neon password that happens to contain one of those substrings will be rejected at startup; regenerate the role password in Neon if that occurs. Do not weaken the validator.

### 4.2 Connection pooling — important nuance

- Neon's Console **"Connection pooling enabled" toggle only changes the connection string it displays**. It does not activate pooling by itself. The application is pooled only if `DATABASE_URL` uses the **pooled hostname containing `-pooler`** (for example `ep-…-pooler.ap-southeast-1.aws.neon.tech`). Verify the actual string copied into Render's secret.
- Neon pools with **PgBouncer in transaction mode** (`max_client_conn=10000`, `default_pool_size = 0.9 × max_connections`, `max_prepared_statements=1000`). The app's 1 instance × (`DB_POOL_SIZE=5` + `DB_MAX_OVERFLOW=10`) = at most 15 client connections, far below any Neon limit.
- `pool_pre_ping=True` in `backend/app/db/session.py` is **beneficial and compatible**: Neon recommends connection validation for pooled connections and scale-to-zero reconnects. No code change needed.
- **Prepared statements:** psycopg 3.2+ supports prepared statements with PgBouncer when PgBouncer ≥1.22, `max_prepared_statements > 0` (Neon: 1000) and **libpq ≥17**. With `psycopg[binary]>=3.1.18` the build installs a current 3.x with bundled libpq, so this will normally work. If the built image ends up on psycopg 3.1.x or libpq <17, server-side prepared statements can misbehave under transaction pooling; the fix would be a settings change (`prepare_threshold=None` / `prepared_max=None`) — **an application-code change, not performed here**. Verify the installed versions during the smoke test.
- **Migrations:** `backend/alembic/env.py` uses the same `DATABASE_URL` as the app. Neon officially recommends a **direct (non-`-pooler`)** connection for schema migrations because transaction pooling does not support session-level `SET`, `PREPARE`/`DEALLOCATE`, or some admin operations. Two options, neither requiring a code change:
  1. Set `RUN_MIGRATIONS=false` on Render and run `alembic upgrade head` once from a trusted machine using the **direct** Neon connection string; or
  2. Keep `RUN_MIGRATIONS=true` with the pooled string and accept the (low, single-instance, small-migration) risk; test it explicitly.
- Neon Free compute **scales to zero after 5 minutes of inactivity and cannot be disabled on Free**; it resumes in a few hundred milliseconds. This is much less disruptive than Render's ~1-minute web-service wake, but it does mean the first query after idle may be slightly slower.

### 4.3 Residual Neon Free limits (not the withdrawn Render-Postgres blocker)

1 GB storage per project, 100 CU-hours/month, 5 GB egress, 6-hour change history, 1 manual snapshot, **no scheduled backups**, and fixed scale-to-zero. Adequate for a limited demo; these are capacity/recovery caveats, not deploy blockers for that scope. If Neon Free allowances are exhausted, compute is suspended until the next billing period or upgrade — data is not deleted.

---

## 5. Required environment variables

Inject these in the Render Dashboard/secret manager. **Do not commit them and do not paste them into `render.yaml`.** No values are quoted here.

### 5.1 Hard requirements for `ENVIRONMENT=production` (startup fails closed otherwise)

| Variable | Requirement |
| --- | --- |
| `ENVIRONMENT` | `production` |
| `DEBUG` | `false` |
| `JWT_SECRET_KEY` | ≥32 chars, ≥10 distinct chars, not a placeholder/known dev value. Pending operator rotation for the value previously identified in `backend/.env`. |
| `BYOK_ENCRYPTION_KEY` | Valid Fernet key, not a known dev value. Pending operator rotation for the value previously identified in `backend/.env`. Losing it makes stored user keys unrecoverable. |
| `DATABASE_URL` | The **Neon pooled** `postgresql+psycopg://…` string with `sslmode=require` (and `channel_binding=require` if supplied). See §4 for the password-substring gotcha and the direct-string migration option. |
| `BACKEND_CORS_ORIGINS` | Real frontend origin(s); no `*`, localhost, or placeholder values. |
| `ALLOW_GLOBAL_OPENAI_FALLBACK` | `false` (production forbids `true`). |
| `JWT_ALGORITHM` | `HS256` (default). |
| `PORT` | `8000` (see §3). |

### 5.2 Conditionally validated

| Variable | Condition |
| --- | --- |
| `EMAIL_NOTIFICATIONS_ENABLED` / `MAIL_FROM` | If email is enabled, `MAIL_FROM` must be a real sender domain. With SMTP blocked on Free, either disable email for the demo or (future change) use an HTTPS provider. |
| `GOOGLE_OAUTH_ENABLED` / `GOOGLE_OAUTH_CLIENT_ID` | Client ID required when OAuth is enabled. Live verification pending. |
| `WHATSAPP_ENABLED` / `WHATSAPP_ACCESS_TOKEN` / `WHATSAPP_PHONE_NUMBER_ID` / `WHATSAPP_VERIFY_TOKEN` | All required when WhatsApp is enabled. Live Meta verification pending. |
| `INTAKE_WEBHOOK_TOKEN` | If set, must not be a placeholder. |

### 5.3 Operational / functional

| Variable | Note |
| --- | --- |
| `RUN_MIGRATIONS` | Default `true`: entrypoint runs `alembic upgrade head` on every start (see §4.2 for the pooled-vs-direct recommendation). |
| `ATTACHMENT_STORAGE_DIR` | Defaults to `/app/var/attachments` in Docker. On Free this is ephemeral — see §8. |
| `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_TIMEOUT`, `DB_ECHO` | Pool defaults 5/10/30/false. Keep small on 512 MB; Neon pooling means a smaller client pool is safe. |
| `OPENAI_API_KEY` | Leave empty under BYOK policy. No production global fallback. |
| `OPENAI_MODEL`, `OPENAI_TIMEOUT_SECONDS`, `AI_*` tuning, `AI_KNOWLEDGE_FILE` | Defaults in `backend/.env.example`. |
| `AI_RATE_LIMIT_PER_MINUTE`, `SLA_HOURS`, `ESCALATION_SWEEP_MINUTES` | Defaults 20 / 24 / 60. |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_USE_TLS`, `SMTP_USE_SSL`, `SMTP_TIMEOUT_SECONDS`, `SMTP_ATTEMPTS` | **Unusable on Render Free** (see §6). Do not treat setting these as a fix. |
| `MAX_UPLOAD_BYTES`, `ALLOWED_UPLOAD_TYPES` | Defaults 5 MiB / `pdf,txt,md`. |
| `API_V1_PREFIX`, `PROJECT_NAME`, `VERSION` | Defaults `/api/v1`, project name, `1.0.0`. |

---

## 6. Build and startup risks

1. **Resource fit is unverified.** Free = 0.1 CPU / 512 MB RAM. The image installs `langgraph==1.2.24`, `langchain-core==1.8.4`, `cryptography`, `psycopg[binary]`, `pypdf`, `reportlab` and `openpyxl`. `pip` installs under 512 MB can be slow or OOM, and Free build minutes are limited. Render publishes no memory guarantee for this dependency set, so runtime fit is **UNKNOWN**, not PASS. See §9.
2. **Migrations at every start.** `RUN_MIGRATIONS=true` runs `alembic upgrade head` before uvicorn. Each Free restart/spin-down repeats it. If Neon is unreachable (e.g. compute resuming or allowances exhausted), startup blocks and `/health` never passes, so Render marks the deploy failed. Use the direct-string option in §4.2 if possible.
3. **`/health` is liveness only.** It deliberately does not touch Neon or providers. Render will report "healthy" even if the database, email, attachments, or AI path is broken.
4. **Production config fails closed.** Missing/placeholder secrets, missing TLS DB URL, wildcard/localhost CORS, or `ALLOW_GLOBAL_OPENAI_FALLBACK=true` prevent startup. Operator rotations were pending at audit time.
5. **SLA worker vs. spin-down.** See §7 — this is a functional limitation, not just a delay.
6. **Database is now external (corrected).** Neon removes Render Postgres's 30-day expiry and Render-side maintenance risk. Residual Neon Free caveats in §4.3 (1 GB, CU-hours, no scheduled backups, scale-to-zero) apply.
7. **Port detection.** The app hardcodes 8000; setting `PORT=8000` explicitly in `render.yaml` removes Render's detection uncertainty.
8. **Zero-downtime assurance.** With one Free instance and an entrypoint migration step there is no rolling validation before traffic switches.

---

## 6a. Free-plan restrictions that remain

| # | Restriction | Official evidence | Impact | Mitigation status |
| --- | --- | --- | --- | --- |
| 1 | **SMTP ports 25/465/587 blocked for Free web services** (port 25 blocked for all services). | `render.com/docs/free`. HTTPS/443 is not restricted. | Default `SMTP_PORT=587` email delivery cannot work. | **Not fixed.** For the demo: disable email or accept in-app-only notifications. HTTPS API is viable but requires a code change (§10). |
| 2 | **Ephemeral filesystem; no persistent disks on Free.** | `render.com/docs/free`, `render.com/docs/disks`. | Attachment bytes under `/app/var/attachments` are lost on redeploy/restart/spin-down while metadata remains in Neon. | **Not fixed.** Demo: avoid attachments or accept loss. Durable fix requires object storage + code change (§8). |
| 3 | **15-minute idle spin-down, ~1 minute wake, arbitrary restarts.** | `render.com/docs/free`. | ~1-minute cold latency, broken scheduled SLA work (§7), unreliable inbound webhook intake. | **Not fixed on Free.** Paid plan required for always-on. |
| 4 | ~~Free Postgres expires after 30 days~~ | **WITHDRAWN** — Render Postgres is not used. | Neon is external; its data is not subject to Render's 30-day expiry. | **Resolved by architecture.** Neon Free caveats in §4.3 remain. |
| 5 | **0.1 CPU / 512 MB RAM.** | `render.com/docs/compute-plans`. | Build/runtime headroom unverified. | **Risk, not proven failure** (§9). |
| 6 | **Unclosed release prerequisites.** | `docs/RELEASE_READINESS.md`. | Rotations, live provider verification, scope sign-off, host approval. | **Not fixed** — governance. |

---

## 7. SLA escalation worker behaviour when Render sleeps

This corrects the earlier one-line statement with the actual mechanism.

**Implementation:** `backend/app/main.py` starts `_escalation_worker()` in the FastAPI `lifespan` only when `ENVIRONMENT=production`. The worker's loop is:

```
while True:
    await asyncio.sleep(ESCALATION_SWEEP_MINUTES * 60)   # default 60 min
    run_escalation_sweep(db)
```

Consequences:

1. **No sweep at startup.** The first sweep happens 60 minutes *after* the process starts, not immediately.
2. **Nothing runs while spun down.** Render stops the Free instance after 15 minutes without inbound traffic. An `asyncio.sleep` timer does not advance when the process is not running, so no sweep occurs during sleep.
3. **Wake restarts the timer.** Render spins up a fresh process from the image on the next request. The worker is created anew and sleeps another full 60 minutes. Render's own health checks should not be relied on to keep the service awake — there is no documented Free-plan keep-warm guarantee.
4. **Practical result:** if demo traffic is intermittent (e.g. a 10-minute session every hour), the process may never remain awake for 60 continuous minutes and **zero automatic escalations will occur**. With continuous traffic, sweeps occur roughly hourly. This is "opportunistic/on-demand", not a scheduler.
5. **Neon interaction:** Neon also scales to zero after 5 idle minutes, but a sweep can only run while the Render process is awake and traffic is keeping Neon warm too. Neon's sub-second resume is not the limiting factor; Render's process lifecycle is.
6. **On wake:** the entrypoint runs `alembic upgrade head` (unless disabled) before uvicorn, adding latency to the ~1-minute cold start.

**Demo implication:** demonstrate SLA escalation by ensuring continuous activity for the full sweep interval, or by triggering/observing the sweep manually; do not claim reliable 24-hour automated escalation on Render Free.

---

## 8. External attachment storage options, including Cloudflare R2

**Current implementation:** `backend/app/services/attachments.py` validates and writes bytes with `Path.write_bytes` / `temporary.replace(destination)` under `ATTACHMENT_STORAGE_DIR`; only `storage_path`, checksum and size go to PostgreSQL. There is **no provider abstraction**. `backend/app/api/routes/tickets.py` exposes upload and metadata-list endpoints but **no byte-download endpoint**.

| Option | Fit | Notes |
| --- | --- | --- |
| Render persistent disk | **Unavailable** | Paid plans only (`render.com/docs/disks`); not an option on Free. |
| Keep local disk on Free | **Demo-only** | Works until the first redeploy/restart/spin-down, then bytes vanish while Neon rows remain — dangling metadata. Acceptable only for a disposable demo with no valued uploads. |
| **Cloudflare R2** | **Best durable $0 option** | S3-compatible API at `https://<ACCOUNT_ID>.r2.cloudflarestorage.com`, region `auto`. Free allowance: **10 GB-month storage, 1 million Class A (write/list) and 10 million Class B (read) operations per month, no egress charges** (`developers.cloudflare.com/r2/pricing`). Easily covers a university demo. Requires an S3 SDK (e.g. `boto3`) and changes to `attachments.py` — **new dependency + code change, not performed**. `storage_path` can be reused as the object key so no schema change is needed. Add a download/presigned-URL endpoint separately (also a code change). |
| Neon Object Storage | **Alternative** | S3-compatible and available on all plans including Free (5 GB/project per month per Neon plans doc). Same code-change requirement as R2; convenient if keeping everything with Neon, but R2's larger free allowance and zero egress make it the stronger fit. |
| Other S3-compatible stores (AWS S3, Backblaze B2) | Feasible | Same integration shape; likely incur storage/egress cost outside free tiers. |

**Verdict:** R2 is technically the right durable answer and fits $0, but it **cannot be enabled without modifying application code and dependencies**. For this correction pass it remains a documented future change; on Render Free today attachments are a demo-only feature.

---

## 9. 512 MB RAM / 0.1 CPU risk assessment

| Phase | Risk | Assessment |
| --- | --- | --- |
| Docker build (`pip install`) | **Medium–High** | Many binary/heavy wheels (`psycopg[binary]`, `cryptography`, `pypdf`, `reportlab`, `openpyxl`, `uvicorn[standard]`, LangGraph stack). Under 0.1 CPU builds are slow; under 512 MB there is a real OOM risk during compilation/install. Free build-pipeline minutes are limited. Not yet observed — no build was run in this audit. |
| Container start (migrations + import) | **Medium** | Importing FastAPI + SQLAlchemy + LangGraph + crypto and running Alembic against Neon (plus Neon resume) must complete within Render's 15-minute health-check window. Likely OK, but unverified. |
| Idle steady state | **Low–Medium** | One uvicorn worker, SQLAlchemy pool of 5 (plus 10 overflow), async SLA task. Python baseline plus these libraries plausibly fits 512 MB, but with little headroom. |
| Concurrent requests / AI graph | **Medium–High** | LangGraph/AI analysis, PDF/XLSX report generation (`reportlab`, `openpyxl`) and 5 MiB attachment handling are memory/CPU intensive. 0.1 CPU will make these slow; concurrent demo users could exhaust memory. |
| Mitigations available without code change | — | Keep **1 uvicorn worker** (Dockerfile default), lower `DB_POOL_SIZE`/`DB_MAX_OVERFLOW` (e.g. 2/3), keep `AI_MAX_*_TOKENS` modest, avoid concurrent report generation and large uploads during the demo, keep `RUN_MIGRATIONS` on but expect cold-start cost. |
| Conclusion | — | **UNKNOWN, not PASS.** A smoke build and a measured run on the target plan are required before relying on it, even for the demo. |

---

## 10. HTTPS email API assessment

- Render blocks **outbound SMTP ports 25/465/587** on Free but does **not** block HTTPS/443. An HTTPS transactional email API is therefore technically viable.
- **Integration seam is narrow:** `backend/app/services/notifications.py` only calls `email_service.is_configured()` and `email_service.send_email(to_address=…, subject=…, body=…)`; `backend/app/api/routes/integrations.py` uses `is_configured()` for the status endpoint. Replacing the SMTP internals of `backend/app/services/email.py` with an HTTPS call would localise the change to that one module plus a new API-key setting. `DeliveryResult` can be returned unchanged, so notification rows, retry status and audit behaviour stay intact. `httpx` is already in `backend/requirements.txt`, so no new HTTP dependency is strictly required.
- **But it is still an application-code change:** `is_configured()` currently requires `SMTP_HOST` and checks only SMTP placeholder domains; a provider based on an API key would need that gate and a new config setting changed. No database schema or migration change is needed. Per the current instructions, **this was not implemented**.
- **Free provider example:** Resend's free tier is 3,000 emails/month with a 100/day cap (`resend.com/pricing`) — ample for a university demo. Brevo/MailerSend-style providers offer similar free quotas. A verified sending domain is required for deliverability.
- **Demo workaround without code change:** set `EMAIL_NOTIFICATIONS_ENABLED=false` (or leave `SMTP_HOST` empty) so the system records in-app notifications only. This is honest as a scoped demo limitation, not a silent failure: existing code marks email rows `failed` if SMTP is attempted but unreachable.

---

## 11. Feature-by-feature verdict (Render Free + Neon)

"Works" assumes the smoke build succeeds, the Neon pooled string with TLS is used, and the pending secret rotations are completed.

| Feature | Verdict | Reason |
| --- | --- | --- |
| JWT authentication, roles/RBAC, user management | **WORKS** | Pure HTTP + Neon writes; no Free-plan restriction. |
| Ticket create/list/update, messages, status workflow | **WORKS** | Core CRUD is unaffected by Render Free limits. |
| In-app notifications | **WORKS** | Persisted in Neon; no outbound transport needed. |
| Audit log | **WORKS** | Database-only. |
| PDF/XLSX ticket reports | **WORKS with caution** | Endpoints exist and generate in-process; memory/CPU risk under 512 MB for large datasets. Fine for a small demo. |
| Admin provisioning CLI | **WORKS (operator-run)** | Run off-platform against Neon; do not expose admin creation publicly. |
| Health/liveness endpoint | **WORKS but shallow** | `/health` does not check Neon or providers; do not treat it as readiness. |
| Alembic migrations | **WORKS with caveat** | Prefer a direct Neon string + `RUN_MIGRATIONS=false` for one-off migration (§4.2). |
| AI analysis — abstention path (no key) | **WORKS** | Designed to abstain when no BYOK key is present. |
| AI analysis — real user BYOK | **CONDITIONAL** | HTTPS to OpenAI on 443 is allowed; requires real user keys, verified Fernet encryption key, and acceptable latency under 0.1 CPU. No global fallback. Live real-user verification is still open. |
| Knowledge document ingestion (`AI_KNOWLEDGE_FILE`) | **CONDITIONAL** | Static file must be available in the image/build context; not a runtime storage feature. |
| Ticket attachment upload | **DEMO ONLY** | Metadata persists in Neon; bytes are lost on restart/spin-down (§8). No download endpoint exists even today. |
| Email notifications over SMTP | **DOES NOT WORK** | Ports 587/465/25 blocked on Free (§6a). |
| Email notifications via HTTPS API | **FEASIBLE, NOT ENABLED** | Clean seam, but requires a code/config change (§10). Resend free tier would cover demo volume. |
| WhatsApp notifications | **CONDITIONAL** | Uses Meta's HTTPS API (443), so not port-blocked; depends on unverified Meta credentials and address overrides. |
| Google OAuth login | **CONDITIONAL** | HTTPS-based; depends on unverified Google OAuth configuration and correct `BACKEND_CORS_ORIGINS`. |
| Inbound HTTP webhook intake | **DEMO ONLY** | HTTPS POST works, but a spun-down service adds ~1-minute wake latency and no keep-warm guarantee. |
| Inbound **email** intake | **DOES NOT WORK** | Depends on inbound mail/SMTP-style transport not available on Free. |
| Automated SLA escalation sweep | **NOT RELIABLE** | In-process async worker cannot run while asleep; timer restarts on wake (§7). |
| Persistent file storage | **DOES NOT WORK** | No persistent disk on Free; R2 requires a code change (§8). |
| Production/public availability, TLS domain, scaling | **FAIL (Render Free platform fit, historical)** | Free plan, then-open governance blockers, spin-down; this is not the current release verdict — see the historical analysis note above. |

---

## 12. Is deployment safe on Render Free?

**Production/public: No.** Do not expose a public production URL, do not apply `render.yaml` for production.

**Private, limited university demo: Conditional Yes**, provided the operator accepts and states these limits up front:

- email notifications disabled (in-app only) or a later HTTPS email API change approved and implemented;
- attachments either not used or treated as disposable (dangling metadata after restarts is accepted);
- no reliance on automatic SLA escalation;
- ~1-minute cold starts and intermittent inbound webhook latency accepted;
- Neon pooled connection string with TLS verified, password validated against the placeholder-pattern rule, and migration strategy chosen (direct string recommended);
- 512 MB / 0.1 CPU smoke build and load check completed;
- all secrets supplied only via Render secrets; no `.env` in Git;
- scope deviation for these degradations signed (VU scope Section L, `L-01`–`L-09`).

Updated conditions before reconsidering production:

1. Formal approval from the operator/university was still outstanding at audit time (historical; the current verified status is in the note above).
2. Operator rotations completed for the identified `backend/.env` OpenAI-shaped and Fernet/BYOK values.
3. Neon connection verified from Render: pooled host, `sslmode=require`, driver, prepared-statement/libpq check, and direct-string migration path tested.
4. Durable attachment storage implemented (R2 or equivalent) — an approved architecture change.
5. HTTPS email provider implemented and sending domain verified, or signed scope approval to omit email.
6. Live verification of Google OAuth, Meta WhatsApp and real-user OpenAI BYOK.
7. Always-on capacity (paid plan or another approved host) for scheduled SLA automation and inbound intake.
8. Resource validation of the actual image on the target plan.
9. Signed deviation approval for outstanding VU scope gaps.

Until then, the authoritative deployment path remains the existing Docker Compose stack; Render Free is suitable only for the constrained demo described above.

---

## 13. Final repository-state verification

- This correction pass changed **only** `docs/RENDER_FREE_PLAN_DEPLOYMENT_AUDIT.md`. `render.yaml` was created in the earlier pass and was not modified here.
- The pre-existing untracked `docs/CLOUDFLARE_ZERO_BUDGET_FEASIBILITY.md` was left unchanged.
- No application code, Dockerfile, dependency file, database schema/migration, frontend, or `.env` file was modified.
- No commit, push, deploy, GitHub change, credential change, or database change occurred.
- No secret, API key, database password, JWT secret, Fernet key, or `.env` file was added to Git.
