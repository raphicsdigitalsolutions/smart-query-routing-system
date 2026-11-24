# Cloudflare Zero-Budget Feasibility Audit

> **Historical analysis note:** This document records the 2026-11-22 zero-budget feasibility analysis. Its FAIL verdicts are historical platform-fit findings, **not** the current release decision. The current verified release status is in `docs/evidence/phase5_live_verification_2026-11-24.json`: technical release artifacts are published and verified; formal institutional/governance approval and live provider verification remain open. Current verdict: **TECHNICAL RELEASE COMPLETE; FORMAL APPROVAL PENDING**.

**Project:** Smart Query Routing System  
**Audit date:** 2026-11-22  
**Mode:** Read-only technical feasibility study  
**Scope:** Existing backend, existing Vercel-compatible frontend/BFF contract, Cloudflare Free/Workers/Containers/Hyperdrive/R2/Queues/Email Service limits.  
**Constraint:** Strict **$0 monthly hosting budget**.  
**Preserved decisions (historical):** Existing Docker deployment path remains authoritative. The 2026-11-22 production/public release was **FAIL — do not deploy** at the time of this analysis; that verdict is superseded by the current status above and is not a current-state deployment instruction.

No source file, configuration file, dependency manifest, Dockerfile, database record, Git object, remote, or deployment setting was modified. Only this report was created. No credentials or secret values are printed.

---

## 1. Executive decision

| Approach | $0 eligibility | Technical fit | Decision |
|---|---:|---|---|
| **A. Existing Docker backend on Cloudflare Containers** | **FAIL** | Technically plausible after decomposition, but Containers are **Workers Paid only** with a **$5/month minimum** | **FAIL under $0 constraint** |
| **B. Adapt existing FastAPI backend to Cloudflare Python Workers** | Theoretically Free-plan eligible, but functionally constrained by **10 ms CPU/request**, ephemeral filesystem, per-request ASGI lifespan, sync stack, and unverified dependencies | Large rewrite required; several subsystems are unsupported or unverified | **FAIL as-is / UNKNOWN after rewrite; not recommended** |
| **C. Keep backend on a separate host; use Cloudflare for DNS, security, Tunnel, and storage** | **CONDITIONAL PASS** for private/low-traffic demonstration; not a production SLA | Preserves existing Docker path and BFF contract; lowest technical risk | **Recommended zero-budget path** |

### Bottom line

Cloudflare **cannot host this backend for $0/month** in its current form:

- **Cloudflare Containers are not available on Workers Free.**
- **Python Workers support FastAPI, but FastAPI support does not imply the rest of this stack is supported.**
- The current backend is built around synchronous SQLAlchemy, synchronous OpenAI SDK calls, synchronous `httpx`, local filesystem attachments, an in-process infinite SLA task, Argon2 password hashing, Fernet encryption, and CLI/Alembic migrations. These do not fit the Workers Free execution model without material redesign.
- Cloudflare Email Sending for arbitrary recipients requires Workers Paid; port 25 SMTP is blocked.
- R2 has a usable free tier, but it does not solve database hosting, CPU limits, background scheduling, or the Node.js BFF runtime.

The only sensible $0 path is **Approach C**: keep the current Docker backend on a container-capable host you already control, put Cloudflare in front with DNS/TLS/WAF and preferably a Cloudflare Tunnel, and optionally back up PostgreSQL plus attachments to R2 within free quotas.

---

## 2. Assessment scale

- **PASS** — Supported by official platform documentation or current code with no material change required.
- **FAIL** — Not available on the target platform, violates a hard limit, or cannot work as currently designed.
- **UNKNOWN** — Not disproven, but requires a proof-of-concept against exact versions and runtime behavior; do not treat as compatible by assumption.

---

## 3. Authoritative current architecture baseline

### 3.1 Backend application

- Entry point: `backend/app/main.py`.
- FastAPI app constructed at `backend/app/main.py:66-88`.
- Lifespan at `backend/app/main.py:49-63`:
  - On startup, if `ENVIRONMENT == "production"`, creates one `asyncio.create_task(_escalation_worker())`.
  - On shutdown, cancels the task, awaits it, and calls `dispose_engine()`.
- `_escalation_worker()` at `backend/app/main.py:34-46` sleeps first, then runs a synchronous escalation sweep.
- Almost all request handlers are synchronous `def`; only root, health, status metadata, and exception handlers are `async def`.
- No FastAPI `BackgroundTasks` are used.
- Alembic migrations run in the container entrypoint, not in ASGI startup: `backend/Dockerfile:35-48,59-60`.
- SQLAlchemy engine/sessionmaker are created at import in `backend/app/db/session.py:30-38`.
- Settings are loaded and validated at import in `backend/app/core/config.py:237-251`.

### 3.2 Existing deployment topology

From `docker-compose.yml`:

- `postgres:16`, internal only, external named volume `smartquerysystem_smartquery_postgres_data`.
- `backend`, internal only on port 8000, attachment volume `smartquery_attachments_data`.
- `frontend`, published on `${FRONTEND_PORT:-3000}`, running the production Next.js BFF.
- Backend and frontend run as non-root UID/GID 10001.
- Secrets are injected at runtime; no real `.env` is baked into images.
- Frontend/BFF calls are same-origin `/api/*`; the BFF attaches the Bearer token server-side.

### 3.3 Existing BFF contract

- `API_BASE_URL` must include the versioned suffix `/api/v1`.
- BFF route list includes `/api/auth/*`, `/api/health`, `/api/reports/{format}`, and catch-all `/api/backend/[...path]`.
- All BFF routes declare `runtime = 'nodejs'`.
- The BFF uses `server-only`, `node:crypto`, `Buffer`, `randomBytes`, and `timingSafeEqual`.
- This is not portable to Python Workers as-is.
- Existing note remains valid: Vercel's approximately 4.5 MB request-body limit conflicts with the project's default 5 MiB upload setting.

---

## 4. Cloudflare platform limits that decide this audit

Sources are official Cloudflare documentation accessed on 2026-11-22.

### 4.1 Workers Free

| Limit | Workers Free |
|---|---:|
| Requests | 100,000/day |
| CPU time | **10 ms/request** |
| Memory | 128 MB/isolate |
| Subrequests | 50/request |
| Simultaneous connections awaiting headers | 6/request |
| Environment variables | 64/Worker |
| Environment variable size | 5 KB |
| Worker size | 64 MiB uncompressed |
| Worker startup | 1 second |
| `waitUntil()` after response | 30 seconds |
| Cron Trigger wall time | 15 minutes |
| Queues standard operations | 10,000/day |
| Queue message retention | 24 hours, non-configurable |
| Hyperdrive queries | 100,000/day |
| Hyperdrive origin connections | approximately 20/configuration |
| Hyperdrive query duration | 60 seconds |
| R2 Standard storage | 10 GB-month/month |
| R2 Class A operations | 1 million/month |
| R2 Class B operations | 10 million/month |

Important interpretation:

- CPU time excludes network waiting, but includes Python execution, schema validation, hashing, PDF parsing, report building, graph compilation, and other local work.
- HTTP requests have no general wall-clock limit while the client remains connected, but the **10 ms CPU cap** still applies on Free.
- `ctx.waitUntil()` is 30 seconds only; it is not a background job system.
- Workers are short-lived; long-lived in-process loops are not a durable scheduling model.
- The Python Workers ASGI adapter drives ASGI lifespan startup/shutdown around requests; it does not provide a permanent uvicorn-style process lifetime.

### 4.2 Python Workers

- Python Workers execute via **Pyodide**, CPython compiled to WebAssembly, inside V8 isolates.
- Official FastAPI support exists through Cloudflare's ASGI server:
  - `from workers import asgi`
  - `Default = asgi.entrypoint(app)`
- Python Workers support pure Python and PyEmscripten wheels plus packages available in Pyodide.
- Official Python Workers docs require `requires-python = ">=3.13"` in the `pyproject.toml` example.
- Filesystem is an **ephemeral in-memory VFS**; data is lost when the isolate is destroyed and is not shared between isolates.
- `threading` and `multiprocessing` are present but **not functional**.
- Several stdlib modules are excluded entirely (`fcntl`, `resource`, `syslog`, `termios`, `venv`, etc.).
- Cloudflare's Hyperdrive Python Workers documentation states:
  - Hyperdrive with Python Workers requires compatibility date `2026-09-08` or later.
  - `psycopg` is the tested/recommended PostgreSQL driver.
  - **Only synchronous SQLAlchemy ORMs are currently supported**; async SQLAlchemy is not supported because greenlet is unavailable.
- Cloudflare's LangChain documentation lists older provided versions (`langchain` 0.1.8, `langchain-core` 0.1.25, `langchain-openai` 0.0.6). It does not document `langgraph==1.2.24` or `langchain-core==1.8.4`.

### 4.3 Containers

- Cloudflare Containers are **available on Workers Paid plan only**.
- Workers Paid has a **$5/month minimum**.
- Containers include monthly allotments on Paid, then bill vCPU, memory, disk, and egress.
- Containers are appropriate for real Linux processes, native dependencies, and existing container images, but they do not satisfy a strict $0 requirement.

### 4.4 Email

- Workers can create outbound TCP sockets, but **port 25 SMTP is prohibited**.
- Cloudflare Email Service sending to arbitrary recipients is **Workers Paid only**.
- Sending to verified destination addresses is free on all plans.
- Cloudflare Email Service authenticated SMTP uses port 465 and requires an onboarded sending domain and API-token-based SMTP credentials.
- Message size limit is 25 MiB including attachments.

---

## 5. Dependency compatibility table

Status applies to **Cloudflare Python Workers/Pyodide**, not Containers. Containers can use the existing Linux wheels because they run a real Python environment.

| Dependency | Declared | Used for | Assessment | Evidence and constraints |
|---|---:|---|---|---|
| `fastapi` | `>=0.115.0` | API framework, schemas, routing, error handlers | **PASS** | Cloudflare officially documents FastAPI with built-in ASGI server. Framework support alone does not cover sync routes or other dependencies. |
| `uvicorn[standard]` | `>=0.30.0` | Local/container ASGI server only | **FAIL / exclude** | Not imported by app code. Cloudflare provides the ASGI server. `[standard]` extras include native packages such as uvloop/httptools/watchfiles and are unnecessary and unverified in Pyodide. Keep for Docker only. |
| `starlette` | undeclared, transitive | `HTTPException`, CORS, responses, streaming | **PASS with caveat** | Pure Python and part of FastAPI stack. `main.py:10` imports it directly, so it should be declared explicitly in any Worker packaging experiment. |
| `pydantic` | `>=2.7.0` | Settings, schemas, agent state, OpenAI structured outputs | **UNKNOWN** | Pydantic v2 depends on native `pydantic-core`. Pyodide lists a compatible pydantic build, but exact `pydantic-core`/pydantic version resolution under `pywrangler` must be proven. Cannot fall back to v1 without breaking validators and OpenAI structured output. |
| `pydantic-settings` | `>=2.3.0` | Settings and production validation | **UNKNOWN** | Inherits pydantic-core risk. `config.py:18,237-242` reads `backend/.env` at import. Worker deployment must rely on injected environment variables/secrets only. |
| `sqlalchemy` | `>=2.0.30` | ORM, sessions, queries, models | **PASS with constraints** | Cloudflare documents synchronous SQLAlchemy support with Hyperdrive; async SQLAlchemy is not supported. Existing app is synchronous, which aligns, but long-lived pool assumptions require review. |
| `psycopg[binary]` | `>=3.1.18` | PostgreSQL DBAPI driver selected by URL | **UNKNOWN** | Cloudflare recommends `psycopg` with Hyperdrive and Pyodide lists psycopg-related packages, but the `[binary]` extra and exact version/transport must be validated. Requires Hyperdrive TCP path, not local database access. |
| `alembic` | `>=1.13.0` | Migrations | **FAIL inside Worker** | Requires CLI lifecycle, migration files, `alembic.ini`, logging config, and DB connection. Keep as a separate job/step; current Docker entrypoint is the supported path. |
| `argon2-cffi` | `>=23.1.0` | Password hashing | **UNKNOWN package / FAIL Free CPU** | Pyodide lists `argon2-cffi` 23.1.0, but Argon2id is memory-hard and CPU-expensive. A hash/verify operation is very likely to exceed the 10 ms Free CPU budget. WebCrypto has no drop-in Argon2 equivalent. |
| `PyJWT` | `>=2.8.0` | HS256 app JWTs and Google RS256 verification | **PASS with caveat** | Pure Python for HS256. RS256 path uses `cryptography`. Google JWKS uses `@lru_cache` with no TTL in `oauth_google.py:30`, which is a poor fit for short-lived isolates. |
| `openai` | `>=1.40.0` | LLM calls, BYOK validation | **UNKNOWN** | SDK is available in Pyodide lists, but current code uses synchronous `OpenAI(...)`, blocking `.parse()`/`.models.list()` calls, and a 60-second workflow deadline. Needs `AsyncOpenAI`, async nodes, and exact dependency proof including `jiter`. |
| `langgraph` | `==1.2.24` | Five-node agent workflow | **UNKNOWN** | Pure Python, but not documented by Cloudflare. Current code uses synchronous `graph.invoke()` and recompiles the graph per run. No `ainvoke`/streaming/checkpointer. |
| `langchain-core` | `==1.8.4` | Pinned transitive companion for LangGraph | **UNKNOWN** | No direct imports in app/evaluations. Cloudflare docs list older langchain versions, so exact modern version compatibility is unverified. |
| `cryptography` | `>=43.0.0` | Fernet BYOK encryption, Google RSA verification | **UNKNOWN** | `cryptography` has native/Rust/OpenSSL components. Pyodide lists a newer version, but exact resolution and Fernet token compatibility must be proven. BYOK rotation CLI must remain outside Worker request path. |
| `python-multipart` | `>=0.0.9` | Multipart upload parsing via Starlette | **UNKNOWN** | Pure-Python fallback exists. Large uploads may use spooled temp files, consuming the ephemeral VFS and 128 MB isolate memory. |
| `pypdf` | `>=5.0.0` | PDF knowledge ingestion | **UNKNOWN** | Pure Python but not in Pyodide's listed package table. Synchronous text extraction over uploads up to 5 MiB can exceed Free CPU budgets. |
| `reportlab` | `>=4.2.0` | PDF report generation | **UNKNOWN** | Used APIs have pure-Python fallbacks, but package is not in Pyodide's listed table. Reports may cover up to 10,000 rows and are fully buffered before response. |
| `openpyxl` | `>=3.1.5` | XLSX report generation | **UNKNOWN** | Pure Python but not in Pyodide's listed table. Entire workbook is held in memory. |
| `httpx` | `>=0.27.0` | WhatsApp, Google JWKS, transitive OpenAI transport | **UNKNOWN** | Pyodide lists httpx, but current code uses synchronous `httpx.get/post` and `lru_cache` JWKS caching. Needs async client/fetch-compatible transport proof. |
| `pytest` | `>=8.2.0` | Tests only | **N/A** | Exclude from Worker bundle. |
| `smtplib` (stdlib) | N/A | Email delivery | **UNKNOWN** | Workers TCP sockets may support stdlib sockets, but port 25 is blocked. Port 465/587 behavior, TLS, and auth with the current code require a live proof. Cloudflare arbitrary-recipient Email Sending requires Paid. |
| `pathlib`/local filesystem (stdlib) | N/A | Attachments, knowledge file, `.env` | **FAIL for persistence** | Worker filesystem is in-memory and per-isolate. Attachments currently use `mkdir`, `write_bytes`, atomic `replace`, and `unlink`; this cannot be durable on Workers. |

Deliberately absent from the project: `python-jose`, `passlib`, `bcrypt`, `pandas`, `numpy`, Google SDKs, Meta SDKs, `langchain-openai`, `subprocess`, `threading`, and `multiprocessing`.

---

## 6. Critical subsystem assessment

| # | Critical subsystem | Assessment | Reason |
|---:|---|---|---|
| 1 | FastAPI framework adapter | **PASS** | Cloudflare officially supports FastAPI through `workers.asgi.entrypoint(app)`. |
| 1a | Existing ASGI entry point and lifespan | **FAIL as-is** | Requires Worker entrypoint change. Cloudflare's ASGI adapter starts/stops lifespan around requests, so the current infinite production SLA task is not a durable background worker. Sync route execution depends on AnyIO threads, which Python Workers do not support functionally. |
| 2 | Backend dependency stack | **FAIL / UNKNOWN** | Multiple dependencies are native, version-sensitive, or unverified (`pydantic-core`, `psycopg[binary]`, `argon2-cffi`, `cryptography`, `langgraph`, `reportlab`, `openpyxl`, `pypdf`). FastAPI support does not make them compatible. |
| 3 | LangGraph, OpenAI, async operations, CPU | **FAIL for Workers Free** | Current graph and SDK calls are synchronous; the workflow has a 60-second deadline; PDF/report/hash work is CPU-heavy; Free CPU cap is 10 ms. Async rewrite and a PoC would be required. |
| 4 | SQLAlchemy/PostgreSQL/Alembic | **UNKNOWN** | Hyperdrive supports synchronous SQLAlchemy and recommends `psycopg`, but external PostgreSQL is still required and Alembic cannot run inside the Worker. Free Hyperdrive does not provide a free database. |
| 5 | Authentication, JWT, Fernet | **FAIL for Free / UNKNOWN after redesign** | HS256/PyJWT is fine; Argon2 is too CPU-heavy for 10 ms; Fernet requires version-proof native/WASM support or a WebCrypto-compatible replacement preserving token format. |
| 6 | PDF/TXT ingestion, PDF/XLSX reports, attachments | **FAIL as-is** | Local filesystem attachments are not durable. Reports and PDF parsing are CPU/memory risky. R2 and row/export caps would be required. |
| 7 | SMTP, Google OAuth, Meta WhatsApp, outbound HTTP | **UNKNOWN / FAIL on Free for arbitrary email** | HTTPS integrations may be possible after async rewrite. Port 25 is blocked; Cloudflare arbitrary-recipient email sending requires Paid. Meta webhook has no POST signature verification; JWKS cache has no TTL. |
| 8 | Background tasks, retries, 24-hour SLA escalation | **FAIL as-is** | No durable in-process background tasks. `waitUntil()` is 30 seconds; Queue retention on Free is 24 hours with 10,000 operations/day. Existing sweep performs blocking DB/SMTP/HTTP work in the async event loop and has no leader election or atomic rate-limit guard. |
| 9 | Environment variables, secrets, Vercel BFF contract | **UNKNOWN / FAIL for direct port** | Worker env limits are 64 variables at 5 KB each. Existing secrets can be mapped to Worker secrets, but the BFF is Node.js runtime and cannot be served by Python Workers. Same-origin cookies, CSRF, and `API_BASE_URL` including `/api/v1` must be preserved. |
| 10 | Cloudflare Free limits, Hyperdrive, R2 | **FAIL for production** | Free quotas may fit a small demo, not a production university system. R2 solves object storage only, not compute, DB hosting, CPU, migrations, or scheduling. |

### Detailed findings by inspection item

#### 6.1 FastAPI application entry point and ASGI startup/lifespan

Cloudflare's documented integration requires a Worker module such as:

```python
from workers import asgi
Default = asgi.entrypoint(app)
```

This is a code change for `backend/app/main.py` or a new Worker wrapper. The current app cannot be deployed unchanged.

Cloudflare's ASGI adapter source drives lifespan startup and shutdown for each request. Therefore:

- `asyncio.create_task(_escalation_worker())` would be created per request and cancelled after the response.
- The then-current escalation schedule would never behave like a persistent hourly job (2026-11-22 analysis).
- `dispose_engine()` would run repeatedly rather than once per process lifetime.
- Any expensive startup work would be repeated; current startup is light, but settings/import work still occurs at module load and must fit the 1-second startup limit.

Route execution is another blocker. Most existing endpoints are synchronous `def` handlers that rely on Starlette's AnyIO worker threadpool. Python Workers list `threading` as non-functional. Whether the Cloudflare ASGI adapter can safely execute this app's sync handlers is **UNKNOWN** and must not be assumed. The safe design would convert routes and services to `async def`, which is a broad rewrite.

#### 6.2 Dependencies

See section 5. The key point is that FastAPI is only the outer web framework. The application also relies on native crypto/hashing, a binary PostgreSQL driver, synchronous ORM, synchronous SDKs, PDF/report libraries, and local filesystem writes. Each must be proven independently.

#### 6.3 LangGraph execution, OpenAI SDK, async operations, CPU

Current workflow:

- Five nodes: classification, routing, knowledge research, response drafting, validation.
- One conditional edge; otherwise linear.
- `graph.invoke()` synchronously per request.
- Graph recompiled per invocation.
- Up to three OpenAI calls, each with up to two attempts and a 20-second timeout.
- Overall workflow deadline: 60 seconds.
- Immediate retry with no backoff.
- AI rate limiter counts rows in a 60-second window but is non-atomic.

On Workers Free:

- Network waiting does not consume CPU time, but graph compilation, prompt redaction, Pydantic parsing, structured output validation, and knowledge scoring do.
- The sync OpenAI client and sync graph path are incompatible with an async-first worker model.
- There is no durable place for a 60-second in-process workflow if the client disconnects.
- CPU-heavy subsystems such as Argon2 hashing, PDF extraction, and report generation are much more likely to break the 10 ms cap than the LLM network wait itself.

#### 6.4 SQLAlchemy, PostgreSQL driver, Alembic

Cloudflare has a favorable path here compared with a pure HTTP-only database: Hyperdrive supports Python Workers, TCP sockets, and synchronous SQLAlchemy. The current app's synchronous SQLAlchemy style is closer to the documented model than an async rewrite would be.

However:

- Hyperdrive is a connection accelerator, not a database. A PostgreSQL origin is still required.
- Hyperdrive Free allows 100,000 queries/day and about 20 origin connections.
- Hyperdrive requires compatibility date `2026-09-08` or later.
- The exact `psycopg[binary]>=3.1.18` resolution must be proven with `pywrangler`.
- The schema itself is portable: it uses generic `JSON`, `VARCHAR` + `CHECK` constraints, standard indexes, and no PostgreSQL-specific extensions. PostgreSQL-specific `with_for_update()` is used only in AI draft approval, and migrations emit `now()` literally.
- Notification and escalation paths write naive UTC values into `TIMESTAMPTZ` columns; this is already a cross-dialect/timezone risk that would need review on any new host.
- Pool sizing is per process (`pool_size=5`, `max_overflow=10`, no `pool_recycle`); aggregate connections must be coordinated with the database connection limit.
- Alembic cannot run in the Worker; it must remain an external migration step/job.
- Existing migration revisions include DML, table rewrites, full-table constraint validation, and a non-concurrent `CREATE INDEX`. They require lock-time planning on any host.
- No advisory lock or leader election protects migrations; scaled replicas must set `RUN_MIGRATIONS=false` and run migrations once externally.
- Production config forbids localhost/non-TLS database URLs, so a local development database cannot simply be reused.

#### 6.5 Authentication, password hashing, JWT, Fernet

- `argon2-cffi` is used for password hashing in `backend/app/core/security.py` with library-default Argon2id parameters; time, memory, and parallelism are not pinned, and login does not call `check_needs_rehash()`.
- Pyodide lists Argon2, but the algorithm is intentionally memory-hard and CPU-expensive.
- Free Workers have 10 ms CPU per request; Argon2 is very likely to exceed that.
- `PyJWT` HS256 is pure Python and should work. Tokens contain `sub`, `role`, `type`, `iat`, and `exp`, but no `jti`, audience, issuer, refresh token, or revocation mechanism. Authorization is mitigated by re-reading the user and role from the database on each request.
- Google RS256 verification relies on `cryptography`.
- BYOK encryption uses Fernet from `cryptography`; exact version compatibility and ciphertext format preservation must be proven.
- BYOK rotation is a batch CLI operation and must stay outside a Worker request.

#### 6.6 PDF/TXT ingestion, reports, attachments

- Knowledge uploads read bytes into memory and extract PDF text with `pypdf`; no raw upload bytes are persisted.
- The optional `AI_KNOWLEDGE_FILE` JSON is re-read from local disk each time an in-memory knowledge repository is constructed.
- Ticket attachments write to the local filesystem with atomic `.part` + `replace` in `backend/app/services/attachments.py`. Metadata and SHA-256 checksums are stored in PostgreSQL.
- There is no attachment download/serve endpoint: `storage_path` is written but never read. Bytes are effectively write-only through the API, and cascade-deleted metadata leaves orphan files on disk.
- Worker VFS is ephemeral and per-isolate; attachments would disappear and would not be shared.
- Reports are generated in `io.BytesIO` using ReportLab and openpyxl. This avoids disk writes but materializes the full document before the response.
- The report route can request up to 10,000 rows.
- PDF parsing and report generation are synchronous CPU work and are likely to exceed Free CPU budgets for realistic inputs.
- Required redesign: attachments and generated reports in R2, metadata/checksums in PostgreSQL, a real retrieval path, lifecycle cleanup for deleted rows, size/row caps, and queued generation for large exports.

#### 6.7 SMTP, Google OAuth, Meta WhatsApp, outbound HTTP

- SMTP uses `smtplib.SMTP`/`SMTP_SSL` with 10-second timeouts and up to three attempts. Workers prohibit port 25. Port 465 may be technically reachable, but the current code against Workers sockets is unverified.
- Cloudflare arbitrary-recipient email sending requires Workers Paid, so the built-in Cloudflare path fails $0.
- Google OAuth uses synchronous `httpx.get` to fetch JWKS, cached forever with `lru_cache`. Short-lived isolates make that cache ineffective and key rotation would require a proper TTL/cache layer.
- Meta WhatsApp outbound uses one synchronous `httpx.post` with a 10-second timeout.
- The WhatsApp webhook implements the GET verification handshake and a token-gated normalized inbound endpoint, but no raw Meta POST signature verification. This is an existing security gap independent of Cloudflare.
- All outbound HTTP calls should become async and use Cloudflare-compatible transports if Workers are ever attempted.

#### 6.8 Background tasks, retries, SLA

- The production SLA worker runs in-process via `asyncio.create_task`.
- It sleeps first, then runs a fully synchronous sweep including DB, email, and WhatsApp calls directly on the async event loop.
- A slow sweep can block all async endpoints for minutes.
- No `BackgroundTasks`, queue, leader election, or durable last-run marker exists.
- On Workers, moving this to Cron + Queues would be a redesign:
  - Cron Trigger CPU on Free is still 10 ms.
  - Queue Free retention is 24 hours and operations are limited to 10,000/day.
  - Escalation itself must be idempotent and chunked.
  - Notifications should be separate queue consumers with retry and dead-letter handling.
- The 24-hour SLA and 10-minute notification deduplication logic exist in the database, but the scheduling mechanism does not port as-is.
- Notification delivery rows are created `pending`, delivered inline, then updated; the 10-minute dedupe is a race-prone query with no unique constraint, and because rows share the caller's transaction, a rollback removes the dedupe record too.
- Audit rows share the business transaction and have no tamper-evident chain; failed operations leave no audit entry and successful entries are mutable in the database.

#### 6.9 Environment variables, secrets, Vercel BFF contract

- Worker environment variable count and size limits are 64 and 5 KB respectively. The project defines a large number of variables, so an inventory and possible consolidation would be needed.
- Real secrets must be Worker secrets or an external secret manager, never `vars`, `NEXT_PUBLIC_*`, source, or images.
- Existing production validation rejects localhost/placeholder secrets and unsafe flags; this should remain.
- The BFF is Node.js runtime and cannot be replaced by Python Workers without rewriting cookie handling, CSRF, streaming, multipart forwarding, and `node:crypto` use in TypeScript or Python.
- If the BFF remains on Vercel, the current upload default conflicts with Vercel's body-size limit; this issue is unchanged.
- Cloudflare routing must preserve same-origin `/api/*` semantics, HttpOnly session cookie, readable CSRF cookie, and `/api/v1` backend prefix.

#### 6.10 Cloudflare Free limits, Hyperdrive, R2

- Free limits are acceptable for a small static/demo workload, not for this system's intended ticket workflow.
- R2 free quota is useful for attachments/backups if carefully bounded.
- Hyperdrive Free still requires a separate PostgreSQL origin.
- Hyperdrive query and connection limits could be exhausted by the synchronous ORM, reports, and frequent short sessions.
- The 100,000 daily request limit and 50 subrequests/request limit are additional ceilings beyond CPU and memory.

---

## 7. Approach comparison

## Approach A — Existing Docker backend on Cloudflare Containers

### Free-tier eligibility and unavoidable costs

**FAIL.** Cloudflare Containers are available only on Workers Paid. Workers Paid has a **$5/month minimum**. Even before usage charges, this exceeds the strict $0 budget.

Additional costs or requirements:

- PostgreSQL origin host.
- Object storage if attachments are moved off local container disk.
- Outbound email provider or Workers Paid Email Sending for arbitrary recipients.
- Container vCPU, memory, disk, and egress beyond included Paid allotments.
- Durable Object usage associated with Containers.

### Required code changes

The existing Compose file is not deployable as a single Cloudflare Container stack. Required changes would include:

- Deploy backend as its own container image.
- Replace local-disk attachments with R2 or another object store.
- Keep PostgreSQL external; configure Hyperdrive or direct external DB access.
- Move Alembic to a deployment step or one-off job.
- Replace the in-process SLA task with a durable scheduler/queue for reliable operation.
- Ensure frontend/BFF reaches the backend through a stable internal or authenticated route.
- Configure real secrets, TLS, CORS, Google OAuth origins, and notifications.

### Unsupported or unverified dependencies

Very few Python dependencies are unsupported inside a real container because Containers run a normal Linux environment. The existing Docker image already builds and passed prior verification.

Unverified areas are architectural rather than library-level:

- Multi-service Compose decomposition.
- Migration execution model.
- Container sleep/cold-start behavior with the SLA sweep.
- Persistent attachment volume replacement.
- External database networking from Cloudflare Containers.

### Performance and execution limitations

- Containers provide substantially more CPU, memory, and filesystem capability than Workers.
- Included Paid allotments are finite; LLM/report workloads and long-running notification sweeps can consume them.
- Cold starts and scale-to-zero can affect latency and scheduled work.
- The current event-loop-blocking escalation sweep remains an application-level defect regardless of host.

### Database and file-storage strategy

- Database: external PostgreSQL, preferably reached through Hyperdrive for pooled access.
- Files: R2 for attachment bytes and generated reports; PostgreSQL stores metadata and checksums.
- Backups: coordinated PostgreSQL dumps plus R2 object copies.

### Security and operational risks

- New infrastructure and secret model requires fresh verification.
- Cloudflare account billing is mandatory, so $0 is impossible.
- Public deployment approval is still absent.
- Existing production blockers remain unchanged.
- Moving state off the known external Docker volume requires careful migration and restore testing.

### Assessment

**FAIL under $0 constraint.** Technically plausible only after accepting paid hosting and a new migration project.

---

## Approach B — Adapt existing FastAPI backend to Cloudflare Python Workers

### Free-tier eligibility and unavoidable costs

Workers Free itself has no monthly fee, but the current system is not realistically deployable under Free limits.

No Cloudflare-hosted database is provided by Hyperdrive; PostgreSQL hosting remains an external requirement. Cloudflare Email Sending for arbitrary recipients requires Paid. If Argon2, PDF parsing, reports, or graph work consistently exceed 10 ms CPU, the only Cloudflare-side remedy is Workers Paid with a higher CPU limit, which breaks $0.

### Required code changes

This is a rewrite, not a port:

1. Add a Worker entrypoint using `workers.asgi.entrypoint(app)`.
2. Create `pyproject.toml` and Wrangler configuration with `python_workers` compatibility flag and compatible compatibility date.
3. Replace uvicorn with the Cloudflare ASGI server for Worker deployments.
4. Remove `.env` file dependence from settings; use injected environment variables/secrets only.
5. Convert synchronous routes and services to async.
6. Replace sync OpenAI with `AsyncOpenAI`, sync graph invocation with `ainvoke`, sync `httpx` with async clients, and sync SQLAlchemy usage with a Worker-supported DB path.
7. Replace local attachment storage with R2.
8. Replace local knowledge file reads with bundled assets, KV, or R2.
9. Move migrations outside the Worker.
10. Replace the in-process escalation loop with Cron + Queues/Durable Objects.
11. Replace SMTP with a Worker-compatible HTTP mail API or prove `smtplib` on allowed ports; Cloudflare arbitrary-recipient sending requires Paid.
12. Replace or revalidate Argon2, Fernet, pydantic-core, psycopg binary, pypdf, reportlab, openpyxl, and LangGraph versions.
13. Re-architect or replace the Node.js BFF if it must also run on Cloudflare.
14. Add size caps and queued processing for PDF ingestion and report generation.
15. Re-run the full test suite, provider verification, migration verification, and release audit.

### Unsupported or unverified dependencies

See section 5. The highest-risk items are:

- `argon2-cffi` CPU/memory under 10 ms Free CPU.
- `psycopg[binary]` exact Pyodide resolution and Hyperdrive transport.
- `pydantic-core` exact resolution.
- `cryptography`/Fernet exact compatibility.
- `langgraph==1.2.24` and `langchain-core==1.8.4` on Python Workers.
- `pypdf`, `reportlab`, `openpyxl` package availability and CPU behavior.
- Starlette sync endpoint execution without functional threads.
- `smtplib` behavior on Worker TCP sockets.

### Performance and execution limitations

- 10 ms CPU/request on Free.
- 128 MB isolate memory including WebAssembly.
- 50 subrequests/request.
- 6 simultaneous connections awaiting headers.
- 64 environment variables at 5 KB each.
- 1-second startup.
- 64 MiB Worker size.
- Ephemeral in-memory filesystem.
- `waitUntil()` only 30 seconds.
- No functional threads or multiprocessing.
- Per-request lifespan behavior through the ASGI adapter.
- Non-durable in-process background tasks.

The current system regularly performs work that is far beyond a typical 10 ms Worker: password hashing, PDF extraction, report generation, Pydantic validation, graph compilation, and attachment checksumming.

### Database and file-storage strategy

- Database: external PostgreSQL through Hyperdrive if the exact driver stack works.
- ORM: only synchronous SQLAlchemy is documented as supported by Cloudflare Hyperdrive for Python Workers.
- Migrations: external one-off job.
- Files: R2/KV; no local disk persistence.
- Reports: generate in memory only with strict row caps, or offload to a queue/container.

### Security and operational risks

- Ephemeral filesystem breaks attachment durability and rollback assumptions.
- Attachment bytes are currently write-only; an R2 migration must also add a retrieval path and lifecycle cleanup, not merely change the write target.
- Per-request lifespan breaks current cleanup/scheduling assumptions.
- Sync handlers may block or fail under Pyodide threading limitations.
- Non-atomic AI rate limiter remains unsafe under concurrency.
- Notification dedupe, SLA sweep coordination, and migration execution have no unique constraints, advisory locks, or leader election.
- Existing migrations include blocking DDL and a non-concurrent index build that need lock-time planning on any host.
- Naive UTC values written into `TIMESTAMPTZ` columns create timezone-dependent comparison semantics.
- JWTs have no revocation or `jti`; Argon2 parameters are not pinned and there is no rehash-on-login.
- JWKS process-lifetime caching is ineffective.
- No Meta webhook POST signature verification.
- Worker logs are capped at 256 KB/request.
- All existing production release blockers remain.
- A Workers migration would be a new, unapproved architecture with no recorded Cloudflare build, deployment, route, or provider verification.

### Assessment

**FAIL as-is. UNKNOWN after a large rewrite. Not recommended under $0.**

---

## Approach C — Keep backend on a separate host; Cloudflare for DNS, security, and storage

### Free-tier eligibility and unavoidable costs

**CONDITIONAL PASS for a private or demonstration deployment.**

Cloudflare components usable at $0:

- Cloudflare DNS.
- Cloudflare proxy/TLS.
- Cloudflare Tunnel to avoid exposing an origin IP.
- Available Free-plan WAF/rate-limiting features, subject to Cloudflare's current plan entitlements.
- R2 Standard within 10 GB-month, 1 million Class A operations, and 10 million Class B operations per month.
- Cloudflare Access free seat limits may be usable for private access; verify current entitlement before relying on it.

Backend host options:

| Host type | $0 status | Caveats |
|---|---|---|
| Existing self-hosted/container machine | **Best $0 fit** | Requires available hardware, bandwidth, uptime, backups, and acceptable ISP terms. Cloudflare Tunnel avoids inbound port forwarding. |
| Oracle Cloud Always Free compute | **Potential $0** | Requires registration/card verification, capacity availability, careful use of Always Free resources, and operational setup. Not guaranteed capacity. |
| Railway Free | **Conditional** | Free plan is usage-limited and services can sleep; current docs describe $0/month with a small included usage amount. Not production-grade. |
| Google Cloud Run free tier | **Conditional** | Generous monthly free usage but requires a billing account; usage outside free tier is chargeable. Container-based and technically compatible. |
| PythonAnywhere Beginner | **Generally unsuitable** | Free tier has very low CPU allowance and limited database/hosting capabilities. |
| Fly.io / Heroku / paid VPS | **FAIL** | No suitable permanent free tier for this stack. |

A strict "$0 and no billing account/card" policy is most safely met only by a self-hosted machine with Cloudflare Tunnel.

### Required code changes

For the self-hosted/Docker variant, **no application source changes are required**:

- Keep `docker-compose.yml` as the deployment path.
- Keep PostgreSQL and attachment volumes.
- Run `cloudflared` on the host and route the public hostname to `http://localhost:${FRONTEND_PORT}`.
- Keep backend unpublishing; only the frontend/BFF should be reachable through the tunnel.
- Keep `API_BASE_URL=http://backend:8000/api/v1` internal to Compose.
- Configure real CORS origins, OAuth origin, cookies, and DNS records.
- Back up PostgreSQL plus the attachment volume; optionally store encrypted backups in R2.

For a remote free-tier Python host, changes depend on the provider, but the Docker image can usually be reused if the provider supports custom containers.

### Unsupported or unverified dependencies

None of the existing Python dependencies are invalidated by this approach because the backend remains a normal Linux container.

Unverified items are platform-specific:

- Provider acceptance of the existing images.
- Volume durability and backup/restore behavior.
- Outbound SMTP and OpenAI/Meta/Google access from that provider.
- Whether free-tier sleep behavior breaks the 24-hour SLA sweep.
- Whether provider egress or request limits fit expected university usage.
- Whether Cloudflare Tunnel terms and local bandwidth are acceptable.

### Performance and execution limitations

- No Workers 10 ms CPU limit.
- Existing 60-second AI workflow, Argon2 hashing, PDF parsing, and report generation remain viable as they were in prior local testing.
- Performance depends entirely on the host.
- Free-tier hosts may sleep, throttle, or impose CPU seconds.
- Self-hosting depends on local bandwidth and uptime.
- This approach preserves the existing single-process SLA worker and its known event-loop-blocking defect; that defect remains a pre-existing risk.

### Database and file-storage strategy

- Keep the external `smartquerysystem_smartquery_postgres_data` volume for PostgreSQL.
- Keep `smartquerysystem_smartquery_attachments_data` for attachment bytes.
- Never delete volumes, prune them, or run `docker compose down -v`.
- Back up PostgreSQL and attachments together.
- Optional R2 use:
  - encrypted database dumps;
  - attachment backup copies;
  - generated report archive;
  - static assets if the frontend is later separated.
- Keep all R2 objects within free quotas and use Standard storage only.

### Security and operational risks

- Cloudflare Tunnel removes the need for inbound firewall openings and reduces origin-IP bypass risk.
- Cloudflare WAF/rate limiting can reduce abuse, but does not replace application authorization.
- Keep JWT, DB, SMTP, Meta, OpenAI, and BYOK secrets backend-side only.
- Keep `NEXT_PUBLIC_*` values public-only.
- Preserve the Node.js BFF and same-origin cookie/CSRF contract.
- Do not expose backend port 8000 or PostgreSQL port 5432 publicly.
- Free tiers do not provide production SLAs.
- The pre-existing data-layer issues remain under Approach C: attachment bytes are write-only with orphan files after cascade deletes, notification dedupe is race-prone, audit rows share the business transaction, and migrations have no concurrency guard and include blocking DDL.
- The 2026-11-22 production release decision was **FAIL** (historical; superseded by the current status at the top of this document).
- No institutional/public deployment approval existed at the time of this study.

### Assessment

**CONDITIONAL PASS** for a private/offline or low-traffic demonstration under strict $0, especially with existing Docker plus Cloudflare Tunnel.

**FAIL for production/public release under the 2026-11-22 study assumptions** (historical; superseded by the current status at the top of this document) until all original release blockers are closed and a hosting provider with adequate reliability and approval is selected.

---

## 8. Recommended deployment architecture

```text
User browser
    |
    | HTTPS
    v
Cloudflare Free zone
  - DNS / TLS / proxy
  - WAF / basic rate controls
  - optional Cloudflare Access for private demo
    |
    | Cloudflare Tunnel (outbound-only from origin)
    v
Existing container host (self-managed or approved $0 host)
    |
    v
docker-compose.yml (unchanged)
    |
    +-- frontend-next:3000  (Node.js BFF, same-origin /api/*)
    |       |
    |       | internal Docker network: http://backend:8000/api/v1
    |       v
    +-- backend:8000 (FastAPI, uvicorn, Alembic entrypoint)
    |       |
    |       +-- postgres:5432 (internal only)
    |       |       `-- external volume smartquerysystem_smartquery_postgres_data
    |       `-- attachment volume smartquery_attachments_data
    |
    +-- cloudflared

Optional, within R2 free quota:
  - encrypted PostgreSQL dump backups
  - attachment backup copies
  - generated report archive
```

### Why this is recommended

1. It preserves the existing, tested Docker path.
2. It avoids Workers CPU/filesystem/threading limits.
3. It avoids Containers' mandatory $5/month charge.
4. It keeps PostgreSQL and attachment volumes under the existing data-safety model.
5. It preserves the Node.js BFF, HttpOnly session cookie, CSRF, and `API_BASE_URL` contract.
6. Cloudflare Tunnel avoids exposing origin ports or IPs.
7. It adds no source, dependency, Dockerfile, or database changes.
8. It is consistent with the existing conditional pass for local/offline demonstration.

### Routing requirements

- Public hostname routes to the frontend/BFF only.
- `/api/auth/*`, `/api/backend/*`, `/api/health`, and `/api/reports/*` remain same-origin on the frontend.
- Do not publish `/api/v1/*` directly through Cloudflare.
- Do not publish PostgreSQL or SMTP ports.
- Use Cloudflare Access or basic network controls if the demo must be private.
- Verify Google OAuth JavaScript origin and CORS origins for the chosen hostname.

### Not recommended

- Do not adapt the current backend to Python Workers under the $0 constraint.
- Do not use Cloudflare Containers while the budget is strictly $0.
- Do not move attachments to R2 without implementing metadata, checksum, lifecycle, and backup consistency.
- Do not replace the BFF with an untested edge implementation.
- Do not start the full stack against the existing external database volume for a public demo until backup/restore and release blockers are resolved.

---

## 9. Complete list of unresolved risks

### Cloudflare platform and cost

1. Cloudflare Containers require Workers Paid and a $5/month minimum; strict $0 is impossible.
2. Workers Free allows only 10 ms CPU per request.
3. Workers Free memory is 128 MB per isolate, including WebAssembly.
4. Workers Free permits 100,000 requests/day.
5. Workers Free permits 50 subrequests/request and 6 simultaneous connections awaiting headers.
6. Workers allow only 64 environment variables at 5 KB each.
7. Worker size is limited to 64 MiB and startup to 1 second.
8. Worker filesystem is ephemeral, in-memory, and not shared.
9. `threading` and `multiprocessing` are non-functional in Python Workers.
10. `waitUntil()` extends execution only 30 seconds after response; it is not durable background processing.
11. Cloudflare Queue Free retention is 24 hours and operations are limited to 10,000/day.
12. Hyperdrive Free is limited to 100,000 queries/day and approximately 20 origin connections per configuration.
13. Hyperdrive requires a separate PostgreSQL origin; it does not provide a database.
14. R2 free quotas are finite: 10 GB-month, 1 million Class A operations, and 10 million Class B operations per month.
15. Cloudflare Email Sending to arbitrary recipients requires Workers Paid.
16. Workers cannot send outbound SMTP on port 25.
17. Free tiers provide no production SLA.
18. Cloudflare WAF/rate-limiting entitlements on the Free plan must be verified before relying on them as security controls.
19. Cloudflare Access free entitlements must be verified before relying on them for private access.

### Python Workers compatibility

20. FastAPI support does not prove compatibility of the rest of the dependency set.
21. Exact `pydantic-core` resolution for the pinned application stack is unverified.
22. Exact `psycopg[binary]>=3.1.18` resolution with Pyodide/Hyperdrive is unverified.
23. `cryptography` version alignment with Fernet ciphertext compatibility is unverified.
24. `argon2-cffi` package availability does not make it feasible under the 10 ms CPU cap.
25. `langgraph==1.2.24` is not documented as supported by Cloudflare Python Workers.
26. `langchain-core==1.8.4` is not documented as supported by Cloudflare Python Workers; Cloudflare documentation lists older LangChain versions.
27. `pypdf`, `reportlab`, `openpyxl`, `python-multipart`, and `alembic` are not in the Pyodide listed-package table and require package/version proof.
28. `jiter`, used by the OpenAI SDK, requires exact WASM compatibility proof.
29. `uvicorn[standard]` extras are unnecessary in Workers and several are native/unverified.
30. Python Workers documentation uses Python 3.13; the current Docker image is Python 3.11, creating an environment skew risk.
31. Starlette sync-route execution relies on AnyIO threads, which are non-functional in Python Workers.
32. Local filesystem calls in attachments and knowledge search cannot be durable on Workers.
33. Alembic requires a real filesystem, CLI lifecycle, and migration files; it cannot run inside a Worker request.

### Application architecture

34. Existing ASGI lifespan creates an infinite production SLA task that is not durable under Cloudflare's per-request adapter behavior.
35. The SLA sweep performs blocking DB, SMTP, and HTTP work directly on the async event loop.
36. There is no leader election for the SLA sweep; multiple workers/processes would duplicate work.
37. Notification deduplication is time-window based and not a full exactly-once guarantee.
38. AI rate limiting uses a count-then-insert pattern and is non-atomic.
39. LLM retry has no backoff and ignores provider `Retry-After`.
40. The AI workflow has a 60-second deadline that does not map cleanly to Worker invocation/background semantics.
41. The graph is recompiled per invocation.
42. OpenAI SDK use is synchronous; BYOK validation is synchronous.
43. Google JWKS caching has no TTL and is ineffective under short-lived isolates.
44. Meta webhook lacks POST signature verification.
45. SMTP delivery has up to 3 attempts × 10 seconds per recipient, sequentially.
46. Reports are fully buffered in memory and may contain up to 10,000 rows.
47. PDF ingestion is synchronous CPU work over uploads up to the configured maximum.
48. Attachment writes use local disk and atomic replace; no R2 migration exists.
49. Generated reports are returned as a single chunk, not truly streamed.
50. Upload spooling could consume scarce isolate memory if attempted on Workers.

### Security, data, and operations

51. Existing production release decision at the time of this 2026-11-22 study was **FAIL — do not deploy** (historical; superseded by the current status at the top of this document).
52. Two known local credential findings remain pending operator rotation; values remain redacted and untouched.
53. Live provider verification remains incomplete for Google OAuth, SMTP, Meta WhatsApp, and real-user OpenAI BYOK.
54. Original VU scope gaps and Section L deviations lack signed approval.
55. Public deployment is not approved.
56. Git history/remote audit remains pending for any eventual public release workflow.
57. No Cloudflare build, route test, deployment test, migration test, or provider verification is recorded.
58. A Cloudflare migration would be a new, unapproved architecture requiring fresh verification and signed deviation approval.
59. Production config rejects localhost, placeholder, and non-TLS database URLs; a new host must provide a compliant database endpoint.
60. CORS and Google OAuth origins must be updated and revalidated for the chosen public hostname.
61. `NEXT_PUBLIC_*` values must remain public-only; backend secrets must never be moved there.
62. The BFF is Node.js runtime and cannot be replaced by Python Workers without a full rewrite.
63. The existing Vercel body-size/upload conflict remains if Vercel is used for the BFF.
64. Backup and restore have not been rehearsed.
65. PostgreSQL and attachment backups must remain coordinated; restoring one without the other creates inconsistency.
66. Retention policy, upload malware scanning, and real-data handling remain unresolved.
67. Application-level security headers and TrustedHost middleware are absent; edge controls must compensate or be added later through an approved change.
68. `/docs`, `/redoc`, and `/openapi.json` are publicly exposed by the current app.
69. Free-tier hosts may sleep or throttle, breaking the expectation of hourly SLA escalation.
70. Self-hosting depends on local power, network uptime, ISP terms, and bandwidth.
71. External free-tier providers may require billing accounts, cards, or could change free-tier terms.
72. No measurable performance baseline exists for Cloudflare-specific designs.
73. Attachment bytes are write-only through the API: `storage_path` is persisted but never read, so there is no download/serve path.
74. Cascade-deleted attachment metadata leaves orphaned files on disk; no cleanup or retention sweep exists.
75. A future R2 attachment migration must add retrieval, lifecycle cleanup, and backup consistency, not only change the write target.
76. `AI_KNOWLEDGE_FILE` is re-read from local disk on each in-memory knowledge repository construction.
77. Argon2id parameters are library defaults and are not pinned; login does not call `check_needs_rehash()` for parameter upgrades.
78. JWTs have no `jti`, audience, issuer, refresh token, or revocation path; they remain valid until expiry.
79. Authorization is mitigated by re-reading the user and role from the database, but the token itself cannot be invalidated.
80. Notification deduplication relies on a 10-minute row query with no unique constraint or lock, and rolls back with the caller's transaction.
81. Audit rows are written inside the business transaction and have no tamper-evident chain; failed operations leave no audit entry.
82. Existing migrations include DML, table rewrites, full-table constraint validation, and a non-concurrent `CREATE INDEX` without lock/statement timeouts.
83. No advisory lock or leader election protects Alembic; scaled replicas must run migrations exactly once externally.
84. SQLAlchemy pool sizing is per process (`pool_size=5`, `max_overflow=10`, no `pool_recycle`) and is not coordinated with PostgreSQL connection limits.
85. Notification and escalation code writes naive UTC timestamps into `TIMESTAMPTZ` columns, creating timezone-dependent comparison semantics.
86. The schema uses generic `JSON`, `VARCHAR` + `CHECK`, and standard indexes; it has no PostgreSQL-specific extension dependency, but PostgreSQL-specific `with_for_update()` is used in AI draft approval.
87. Google JWKS caching has no TTL and no refetch on unknown `kid`; key rotation currently requires a process restart.
88. SMTP delivery is sequential per recipient with up to 3 attempts × 10 seconds, so a single ticket event can block for minutes.
89. Reports are fully materialized in memory before the single-chunk response, with routes allowing up to 10,000 rows.
90. Upload spooling and attachment checksumming consume isolate memory and CPU if attempted on Workers.

---

## 10. Final recommendation

Do **not** migrate the backend to Cloudflare Python Workers or Cloudflare Containers under the current $0 requirement.

Adopt **Approach C** only for a controlled, private, low-traffic demonstration:

1. Keep the existing Docker Compose stack unchanged.
2. Put Cloudflare in front with DNS, TLS, proxying, and preferably Cloudflare Tunnel.
3. Keep backend and PostgreSQL unpublished.
4. Preserve the Node.js BFF and same-origin API contract.
5. Keep backups coordinated between PostgreSQL and attachments.
6. Use R2 only within free quotas and only for encrypted backups/artifacts.
7. Preserve the then-current production release decision: **FAIL — do not deploy** (historical 2026-11-22 status; superseded by the current status at the top of this document).

Any future move to Workers or Containers requires a separate approved migration project, exact dependency proof-of-concept, new architecture documentation, full regression testing, provider verification, and renewed release approval.

---

## 11. Official references consulted

- Cloudflare Python Workers: https://developers.cloudflare.com/workers/languages/python/
- Cloudflare Python Workers FastAPI integration: https://developers.cloudflare.com/workers/languages/python/packages/fastapi/
- Cloudflare Python Workers packages: https://developers.cloudflare.com/workers/languages/python/packages/
- Cloudflare Python Workers standard library: https://developers.cloudflare.com/workers/languages/python/stdlib/
- Cloudflare Python Workers FFI: https://developers.cloudflare.com/workers/languages/python/ffi/
- Cloudflare Python Workers LangChain documentation: https://developers.cloudflare.com/workers/languages/python/packages/langchain/
- Cloudflare Workers limits: https://developers.cloudflare.com/workers/platform/limits/
- Cloudflare Workers pricing: https://developers.cloudflare.com/workers/platform/pricing/
- Cloudflare Hyperdrive overview: https://developers.cloudflare.com/hyperdrive/
- Cloudflare Hyperdrive pricing: https://developers.cloudflare.com/hyperdrive/platform/pricing/
- Cloudflare Hyperdrive limits: https://developers.cloudflare.com/hyperdrive/platform/limits/
- Cloudflare Hyperdrive with Python Workers: https://developers.cloudflare.com/hyperdrive/examples/python-workers/
- Cloudflare Containers: https://developers.cloudflare.com/containers/
- Cloudflare Containers pricing: https://developers.cloudflare.com/containers/platform/pricing/
- Cloudflare R2 pricing: https://developers.cloudflare.com/r2/pricing/
- Cloudflare Queues pricing: https://developers.cloudflare.com/queues/platform/pricing/
- Cloudflare Queues limits: https://developers.cloudflare.com/queues/platform/limits/
- Cloudflare Workers Context API: https://developers.cloudflare.com/workers/runtime-apis/context/
- Cloudflare TCP sockets: https://developers.cloudflare.com/workers/runtime-apis/tcp-sockets/
- Cloudflare Email Service: https://developers.cloudflare.com/email-service/
- Cloudflare Email Service pricing: https://developers.cloudflare.com/email-service/platform/pricing/
- Cloudflare Email Service limits: https://developers.cloudflare.com/email-service/platform/limits/
- Cloudflare Tunnel: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/
- Cloudflare `workers-py` ASGI adapter source: https://github.com/cloudflare/workers-py/blob/main/packages/runtime-sdk/src/workers/asgi.py
