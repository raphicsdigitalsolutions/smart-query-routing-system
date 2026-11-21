# Phase 7 Test Report — Smart Query Routing System

This report records commands that were actually executed in this workspace. It does **not** claim
live Google, SMTP, Meta WhatsApp, or OpenAI verification. Those checks require real provider
credentials that were not supplied. No public deployment was performed.

Test host: Windows/PowerShell. Backend commands were run from `backend/` with the project virtual
environment. Frontend commands were run from `frontend-next/`. Docker commands were run from the
repository root.

## 1. Summary

| Area | Final/local result | Notes |
| --- | --- | --- |
| Backend automated suite | **187 passed, 17 warnings in 294.79s** | Final run after the release-hardening changes. Warnings are pre-existing LangSmith `asyncio.iscoroutinefunction` deprecations. |
| Backend compile | Passed | `python -m compileall -q app tests evaluations`, no output. |
| Migration state | Head `feedf21773e1`; no drift | `alembic current` and `alembic check` against the local development database. |
| OpenAPI | **41 paths** | Confirmed from `app.main.app.openapi()` after adding ticket attachments and the WhatsApp verification handshake. |
| Frontend static checks | Passed | Final rerun after the attachment UI work: typecheck, lint, and production build passed; 13/13 static pages generated. |
| Docker backend image | Built successfully | `docker build -t smartquery-backend:phase7 ./backend` exited 0 against the final backend source. |
| Docker frontend image | Built successfully | First smoke exposed a missing-runtime-TypeScript defect; the Dockerfile was fixed, the image was rebuilt, and the final container passed health checks. |
| Compose validation | Passed | Both `docker-compose.yml` and `docker-compose.db.yml` pass `config`; the full-stack file also passed `config --quiet` after the attachment volume was added. |
| Isolated container smoke / persistence | Passed | Disposable containers/volumes were used. Backend and frontend became healthy, Alembic head was applied in-container, `alembic_version` survived a PostgreSQL restart, BFF session/401 checks passed, and all scratch resources were removed. |
| Live provider checks | Blocked | Real Google OAuth, SMTP, Meta WhatsApp, and OpenAI credentials were not available. |
| Public deployment | Not performed / not approved | No host, DNS, TLS, registry push, or provider configuration was changed. |

## 2. Backend commands and exact results

### 2.1 Full suite

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
```

Result:

```text
........................................................................ [ 46%]
........................................................................ [ 92%]
............                                                             [100%]
============================== warnings summary ===============================
.venv\Lib\site-packages\langsmith\_internal\_beta_decorator.py:92: 17 warnings
  C:\Users\user\OneDrive\Desktop\SmartQuerySystem\backend\.venv\Lib\site-packages\langsmith\_internal\_beta_decorator.py:92: DeprecationWarning: 'asyncio.iscoroutinefunction' is deprecated and slated for removal in Python 3.16; use inspect.iscoroutinefunction() instead
    if asyncio.iscoroutinefunction(func):

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
187 passed, 17 warnings in 294.79s (0:04:54)
```

### 2.2 Focused regression runs

These were run before the final full-suite rerun and cover the Phase 7 risk areas individually:

| Command | Result |
| --- | --- |
| `python -m pytest -q tests/test_byok.py` | `26 passed` |
| `python -m pytest -q tests/test_knowledge.py` | `24 passed` |
| `python -m pytest -q tests/test_agent_evaluation.py` | `8 passed` |
| `python -m pytest -q tests/test_analytics.py tests/test_audit.py tests/test_announcements.py tests/test_leave.py tests/test_reports.py tests/test_oauth.py` | `34 passed, 17 warnings in 111.27s` |
| `python -m pytest -q tests/test_ai_api.py::test_ai_runs_are_rate_limited_per_user` | `1 passed` |
| `python -m pytest -q tests/test_attachments.py tests/test_integrations.py tests/test_tickets.py` | `32 passed, 17 warnings in 43.34s` |
| `python -m pytest -q tests/test_release_hardening.py tests/test_byok_rotation.py tests/test_notifications.py` | `38 passed, 17 warnings in 20.72s` |
| Staff-assignable-user regression tests in `test_tickets.py` | Passed; the staff AI 403 regression is covered by the final full suite. |

### 2.3 Compile, migration, and route checks

```powershell
.\.venv\Scripts\python.exe -m compileall -q app tests evaluations
.\.venv\Scripts\python.exe -m alembic current
.\.venv\Scripts\python.exe -m alembic check
.\.venv\Scripts\python.exe -c "from app.main import app; print(len(app.openapi()['paths']))"
```

Results:

- `compileall`: exit 0, no output.
- `alembic current`: `feedf21773e1 (head)`.
- `alembic check`: `No new upgrade operations detected.`
- OpenAPI path count: `41`. New paths are
  `/api/v1/integrations/whatsapp/webhook` and `/api/v1/tickets/{ticket_id}/attachments`.

### 2.4 Local database safety check

A read-only row-count query against the local development database reported zero records in all
Phase 7 tables and no temporary Phase 7 test data. No production records were deleted. The exact
counts recorded were:

```text
users=1, departments=0, tickets=0, messages=0, analyses=0, status_history=0,
audit=0, knowledge=0, notifications=0, announcements=0, leave=0,
agent_runs=0, user_api_keys=0
```

## 3. Evidence by requirement area

| Area | Evidence |
| --- | --- |
| Staff AI authorization fix | `tests/test_tickets.py` regression tests for role-scoped assignable-user lookup and the assigned-staff workflow; included in the final suite. |
| BYOK | `tests/test_byok.py` covers encryption at rest, add/validate/replace/delete/status, user isolation, no secret exposure, and production fallback policy. LLM and agent services resolve the requesting user's key. |
| Approved knowledge | `tests/test_knowledge.py` covers upload validation, HOD/admin approval, versioning, deactivation, citations, and approved-only retrieval. |
| Agent evaluation | `backend/evaluations/dataset.json`, `backend/evaluations/evaluate.py`, `tests/test_agent_evaluation.py`, and generated `backend/eval_reports/evaluation.json` / `evaluation.md`. The synthetic-data caveat is explicit. |
| Notifications and SLA | `tests/test_notifications.py` and `tests/test_escalation.py` cover fake-SMTP retries/dedupe/audit, internal-note suppression, unapproved-draft suppression, deterministic 24-hour escalation, and repeat-safe sweeps. |
| Roles, ownership, internal notes | `tests/test_auth.py`, `tests/test_tickets.py`, and the new `tests/test_attachments.py` cover cross-user isolation, role permissions, internal-note privacy, and attachment visibility. |
| Analytics, reports, announcements, leave, audit, OAuth | Focused run above: 34 passed. Live OAuth remains blocked. |
| Inbound integrations and ticket attachments | Focused run above: 32 passed. Attachment bytes are written outside the web root; only metadata and checksums are stored in the database. |
| AI abuse control | `tests/test_ai_api.py::test_ai_runs_are_rate_limited_per_user`: 1 passed, plus final suite. |

## 4. Frontend commands and results

Final rerun after the ticket-attachment UI work:

```powershell
cd frontend-next
npm run typecheck   # exit 0, no output
npm run lint        # exit 0, no output
npm run build       # exit 0
```

`npm run build` compiled successfully in 35.1s, passed lint and type validation, and generated
13/13 static pages. The ticket detail route `ƒ /tickets/[ticketId]` was built at 19.6 kB with a
179 kB first load. Phase 7 routes remain present. Files added/changed for this UI are
`src/lib/api/types.ts`, `src/lib/api/endpoints.ts`, `src/components/tickets/TicketAttachments.tsx`
(new), `src/components/tickets/TicketDetail.tsx`, and `src/app/api/backend/[...path]/route.ts`.
The BFF now forwards multipart uploads as raw bytes so binary files are not corrupted by UTF-8 text
decoding. No live authenticated upload was exercised against a running backend; the backend path is
covered by the API tests in §2.

## 5. Docker and Compose commands and results

| Command | Result |
| --- | --- |
| `docker compose -f docker-compose.db.yml config` | Exit 0; unchanged DB-only file. |
| `docker compose -f docker-compose.db.yml config --quiet` | Exit 0. |
| `docker compose -f docker-compose.yml config` | Exit 0. |
| `docker compose -f docker-compose.yml config --quiet` | Exit 0 after the attachment volume and `ATTACHMENT_STORAGE_DIR` were added. |
| `docker compose version` | `Docker Compose version v5.6.1`. |
| `docker build -t smartquery-backend:phase7 ./backend` | Exit 0; final source tree built and tagged. |
| `docker build -t smartquery-frontend:phase7 ./frontend-next` | First build hit the 600s harness timeout after tagging; container smoke then exposed a runtime TypeScript defect. After the Dockerfile fix, the final rebuild exited 0 and tagged `smartquery-frontend:phase7`. |
| `docker build -t smartquery-backend:release-audit ./backend` | Exit 0 after recursive `.dockerignore` fixes; context dropped from 93.72 kB to 5.82 kB and no `.pyc` files were present in the rebuilt image. |
| `docker build -t smartquery-frontend:release-audit ./frontend-next` | Exit 0; image tagged for final secret-content inspection. |

No command used `down -v`, deleted a volume, or recreated the existing production database volume.

### 5.1 Isolated scratch smoke test (backend + PostgreSQL)

An isolated Docker network with disposable volumes (`sq7-smoke-pg`, `sq7-smoke-attachments`) was used.
The existing `smartquery-postgres` container and the external
`smartquerysystem_smartquery_postgres_data` volume were not recreated, stopped, or deleted.
Throwaway production-mode secrets were generated for the smoke container only.

Results:

```text
postgres_ready=True
backend_health=healthy
backend_health_body={"success":true,"status":"healthy"}
migration_version=feedf21773e1
postgres_ready_after_restart=True
migration_version_after_restart=feedf21773e1
backend_health_after_restart=healthy
```

The image entrypoint ran `alembic upgrade head` successfully inside the container. A PostgreSQL
container restart with the same scratch volume preserved the migration row. Two earlier attempts to
pass a JSON `BACKEND_CORS_ORIGINS` value through PowerShell failed with a settings parse error; the
final smoke run omitted that optional override and used the image default. This was a local command
quoting issue, not an application failure.

### 5.2 Frontend container smoke — defect found and corrected

The first tagged frontend image was started on the scratch network. It was unhealthy and served no
HTTP responses. Container logs showed:

```text
⚠ Installing TypeScript as it was not found while loading "next.config.ts".
npm error code EACCES
npm error path /app/node_modules/@alloc/quick-lru
Failed to install TypeScript, please install it manually to continue
⨯ Failed to load next.config.ts
```

Root cause: `next start` loads `next.config.ts` at runtime, but `typescript` is a dev dependency and
is omitted by `npm ci --omit=dev`. The non-root runtime then attempted an ad-hoc install and lacked
write permission. This was a real packaging defect found by the smoke test, not a test harness error.

Fix applied to `frontend-next/Dockerfile`: copy the already-installed `typescript` package from the
`deps` stage into the production runtime layer before switching to the non-root user. Core ticket
operations were never affected because this is frontend packaging only. The final rebuild exited 0.

### 5.3 Final isolated frontend smoke and BFF checks

The corrected image was started on the scratch network with `API_BASE_URL` pointing at the scratch
backend. Results:

```text
frontend_health=healthy
frontend_health_http=200 body={"success":true,"status":"healthy"}
login_page_http=200 bytes=20059
backend_health=healthy
session_http=200 body={"user":null,"csrfToken":"<redacted>","expiresIn":null}
protected_http=401
frontend_log: Ready in 8.7s
```

`GET /api/health` confirmed the BFF could reach FastAPI. `GET /api/auth/session` bootstrapped a guest
session and CSRF token. An unauthenticated `/api/backend/auth/me` request returned 401 as expected.
All scratch containers, the scratch network, and both scratch volumes were then removed. The
existing `smartquery-postgres` container remained `Up (healthy)` throughout.

## 6. Final release-hardening verification

These checks were run after the security remediation and are additional to the earlier Phase 7 evidence.

| Check | Command / method | Result |
| --- | --- | --- |
| Strict production config regression | `.\.venv\Scripts\python.exe -m pytest -q tests/test_release_hardening.py tests/test_byok_rotation.py tests/test_notifications.py` | `38 passed, 17 warnings in 20.72s`. Covers placeholder/weak JWT and Fernet rejection, unsafe production settings, internal Compose DB exception, safe BYOK rotation dry-run/commit, undecryptable-row abort, and sanitized provider errors. |
| Full backend suite | `.\.venv\Scripts\python.exe -m pytest -q` | `187 passed, 17 warnings in 294.79s`. |
| Frontend static checks | `npm run typecheck`; `npm run lint`; `npm run build` | All exit 0; `next build` compiled and generated 13/13 static pages in 35.1s. |
| Compose validation | `docker compose -f docker-compose.db.yml config --quiet`; `docker compose -f docker-compose.yml config --quiet` | Both exit 0; `docker compose version` reported v5.6.1. |
| Redacted current-tree secret scan | Python scanner over 310 non-generated text files; pattern classes and locations only, no values | Three findings, all in `backend/.env`: `OPENAI_API_KEY` at line 42 (key pattern plus non-placeholder assignment) and `BYOK_ENCRYPTION_KEY` at line 51 (Fernet-key shape). Test fixtures and `.env.example` placeholders were classified as informational. No secret value was printed. |
| Git history / staged / untracked audit | `git rev-parse --is-inside-work-tree`; `git status --short --untracked-files=all`; read-only scans | Git repository is present. The 307 untracked files were audited read-only (306 text files and 1 PDF); PASS for secrets, credentials, PII, and artifacts. Zero files are staged and `backend/.env` is ignored. No commit, remote, or push exists, so history/remote audit remains pending. |
| Backend image secret/content audit | `docker run --rm --entrypoint sh smartquery-backend:release-audit -c 'find ...'` and `grep -RIl ...` | No `.env*`, key/certificate files, database files, logs, backups, temp files, generated reports, attachment files, tests, `.pyc` files, or secret-pattern matches. Runtime user `app`, workdir `/app`. |
| Frontend image secret/content audit | `docker run --rm --entrypoint sh smartquery-frontend:release-audit -c 'find ...'` and `grep -RIl ...` | No `.env*`, key/certificate files, npmrc, logs, backups, temp files, or secret-pattern matches. Runtime user `nextjs`, workdir `/app`. |

The two `backend/.env` findings are treated as compromised. They were not read into output, copied, changed, rotated, or deleted by this audit. Rotation remains an operator action.

## 7. Explicitly blocked checks

| Check | Why it was not performed |
| --- | --- |
| Live OpenAI key validation / live evaluation | Requires an explicitly configured personal OpenAI key. Production has no global fallback. |
| Live Google OAuth sign-in | Requires a real Google Cloud OAuth client ID and registered JavaScript origin. |
| Live SMTP delivery | Requires real SMTP credentials and a verified `MAIL_FROM` domain. |
| Live Meta WhatsApp send and webhook registration | Requires a real Meta Cloud API token, phone number ID, and webhook verification token. |
| Public deployment | Not approved. No host, DNS, TLS, image registry, or monitoring configuration was changed. |
| Browser-level accessibility automation | No committed Next.js e2e/accessibility suite exists. Phase 6.1 manual UI audit is historical evidence only. |

## 8. Explicit pending implementation items

These items are tracked in `docs/MASTER_REQUIREMENTS_CHECKLIST.md` Section L and are not claimed as
complete:

- Instructor-level automatic assignment (department auto-routing is implemented; direct instructor
  selection remains manual).
- Live status polling/SSE (on-demand tracking works; automatic refresh is not implemented).
- Password-login/registration audit events (Google login is audited; email session events are not).

## 9. Reproduction order

1. Copy the example env files documented in `README.md`; fill secrets only in local/operator stores.
2. From `backend/`, run `pip install -r requirements.txt`, then the Python commands in §2.
3. From `frontend-next/`, run `npm ci`, then the commands in §4.
4. From the repository root, run the Compose and build commands in §5.
5. Use `docs/DEPLOYMENT_GUIDE.md` for provider setup, backup, restore, rollback, and health checks.
