# Phase 7 Test Report — Smart Query Routing System

This report records the Phase 7 commands that were actually executed in this workspace, plus the
2026-11-24 final reruns and release verification. It does **not** claim live Google, SMTP, Meta
WhatsApp, or real-user OpenAI BYOK verification; those checks require real provider credentials that
were not supplied. A later hackathon deployment and its live smoke checks are recorded separately in
`docs/HACKATHON_DEPLOYMENT_REPORT.md`. Final evidence is indexed in §10.

**Final status: TECHNICAL RELEASE COMPLETE; FORMAL APPROVAL PENDING.** Earlier `FAIL — DO NOT DEPLOY`
wording in this report is historical/superseded by the 2026-11-24 final verification.

Test host: Windows/PowerShell. Backend commands were run from `backend/` with the project virtual
environment. Frontend commands were run from `frontend-next/`. Docker commands were run from the
repository root.

## 1. Summary

| Area | Final/local result | Notes |
| --- | --- | --- |
| Backend automated suite | **229 passed, 17 warnings in 410.30s (0:06:50)** | FINAL full rerun from `backend/`: `.\.venv\Scripts\python.exe -m pytest -q`; 0 failed/errors (`docs/evidence/final_backend_test.json`). Warnings are pre-existing LangSmith `asyncio.iscoroutinefunction` deprecations. Older 187/202/218/225 counts and the earlier 264.12s/292.01s timings are historical. |
| Focused escalation, ticket, notification & audit tests | **42 passed, 17 warnings in 70.95s (0:01:10)** | `tests/test_escalation.py` (including manual escalation/de-escalation history, audit & deduplicated permission-scoped notifications), `tests/test_escalation_serverless.py`, `tests/test_tickets.py`, `tests/test_ticket_updates.py`, `tests/test_notifications.py`, `tests/test_audit.py`. |
| Focused AI consistency, agent, BYOK, knowledge & evaluation tests | **50 passed, 17 warnings in 32.74s** | `tests/test_ai_consistency.py`, `tests/test_ai_agents.py`, `tests/test_ai_api.py`, `tests/test_byok.py`, `tests/test_knowledge.py`, `tests/test_agent_evaluation.py`. |
| Focused malware/attachment tests | **10 passed, 17 warnings in 7.63s** | `tests/test_malware_scan_service.py` + `tests/test_attachment_malware.py`; integrate with a real ClamAV image locally (see §6.1). |
| Browser E2E + accessibility | **12 passed in 2.0m** | `npm run test:e2e` in `frontend-next/`; `pretest` `next build` passed (12/12 pages). Playwright + axe; no serious/critical axe violations on login, student workspace or ticket detail; verifies escalation/de-escalation history and staff notifications (`docs/evidence/e2e_axe_result.json`; see §4.1). |
| Frontend polling unit tests | **3 passed (273ms tests / 14.30s run)** | Vitest `useTicketStatusPolling.test.tsx`; typecheck (`tsc --noEmit`) and lint (`eslint .`) passed with 0 errors/warnings (see §4.1). |
| Backend compile | Passed | `python -m compileall -q app tests evaluations`, no output. |
| Migration state | Head `feedf21773e1`; no drift | `alembic current` and `alembic check` against the local development database. |
| OpenAPI | **41 paths** | Confirmed from `app.main.app.openapi()` after adding ticket attachments and the WhatsApp verification handshake. |
| Frontend static checks | Passed | Final rerun on Next.js 16.4.6 with `next build --webpack`: typecheck, lint, and production build passed; 12/12 static pages generated. |
| Docker backend image | Built successfully | `docker build -t smartquery-backend:phase7 ./backend` exited 0 against the final backend source. |
| Docker frontend image | Built successfully | First smoke exposed a missing-runtime-TypeScript defect; the Dockerfile was fixed, the image was rebuilt, and the final container passed health checks. |
| Compose validation | Passed | Both `docker-compose.yml` and `docker-compose.db.yml` pass `config`; the full-stack file also passed `config --quiet` after the attachment volume was added. |
| Isolated container smoke / persistence | Passed | Disposable containers/volumes were used. Backend and frontend became healthy, Alembic head was applied in-container, `alembic_version` survived a PostgreSQL restart, BFF session/401 checks passed, and all scratch resources were removed. |
| Backup/restore rehearsal | PASS (local disposable) | `docs/evidence/backup_restore_rehearsal.json`; production not touched (see §6.1). |
| Secret audit | Findings recorded; no rotation | `docs/evidence/secret_audit.json` + `docs/SECRET_AUDIT_REMEDIATION_PLAN.md` (see §6.1). |
| npm audit | **0 vulnerabilities** (full and production-only) | Final: `docs/evidence/npm_audit_final_2026-11-24.json`, `docs/evidence/npm_audit_prod_final_2026-11-24.json`. The 6-package 2026-11-23 result is historical/superseded (see §6.2, §6.4). |
| Live provider checks | Blocked | Real Google OAuth, SMTP, Meta WhatsApp, and OpenAI credentials were not available. |
| Live hosted escalation cron | NOT VERIFIED | Code/config local-verified only; see §6.1. |
| GHCR package existence / anonymous pull | Verified read-only | `docs/evidence/ghcr_readonly_investigation.json`: package exists, anonymous pull capable, digest `sha256:417e017081a460adfe310236e13b3e117cb972c11c5c93370968aa866a2b0f0f` matches recorded/local. |
| GHCR publication of current changes | Blocked | Missing `write:packages`; no registry write or push attempted (see §6.2). |
| Public deployment | Hackathon deployment executed and live-verified | **TECHNICAL RELEASE COMPLETE; FORMAL APPROVAL PENDING** — formal institutional sign-off and live provider verification remain open. See `docs/HACKATHON_DEPLOYMENT_REPORT.md`, `docs/RELEASE_READINESS.md` and §10. |
| Git state | Verified | release-evidence commit `2cb5595ee7a38c85c63223079dc9d17a290ed089` (`b51dd31` → `7ad663e` → `eb30f92` → `2cb5595`); clean working tree after the final commit. |
| `release-v1` database | Read-only verification PASS | `docs/evidence/release_v1_readonly_verification_2026-11-24.json`: Alembic `feedf21773e1`, 17 public tables, `departments=4`, `users=0`, `tickets=0`, `writes_performed=false`. See §10. |

## 2. Backend commands and exact results

### 2.1 Full suite

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
```

Result (final full run; this is the current count):

```text
============================== warnings summary ===============================
.venv\Lib\site-packages\langsmith\_internal\_beta_decorator.py:92: 17 warnings
  C:\Users\user\OneDrive\Desktop\SmartQuerySystem\backend\.venv\Lib\site-packages\langsmith\_internal\_beta_decorator.py:92: DeprecationWarning: 'asyncio.iscoroutinefunction' is deprecated and slated for removal in Python 3.16; use inspect.iscoroutinefunction() instead
    if asyncio.iscoroutinefunction(func):

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
229 passed, 17 warnings in 410.30s (0:06:50)
```

The warnings are pre-existing LangSmith `asyncio.iscoroutinefunction` deprecations. Earlier
`187 passed`, `202 passed`, `218 passed` and `225 passed` lines elsewhere in this report are
explicitly historical Phase 7 results, not the current total (`docs/evidence/final_backend_test.json`).

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
| `python -m pytest -q tests/test_malware_scan_service.py tests/test_attachment_malware.py` | `10 passed, 17 warnings in 7.63s` (final focused malware/attachment run; see §6.1 for the real-ClamAV evidence). |
| Staff-assignable-user regression tests in `test_tickets.py` | Passed; the staff AI 403 regression is covered by the final full suite. |
| `tests/test_instructor_routing.py`, `tests/test_ticket_updates.py`, `tests/test_escalation_serverless.py`, `tests/test_auth_audit.py`, `tests/test_token_expiry.py` | Passed in the final full suite; scope and caveats are summarised in §6.1. |

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

### 2.5 FR-04b / FR-13 implementation verification

These runs were added after deterministic instructor routing and leave-aware exclusion were
implemented. The historical Phase 7 results above are left unchanged.

| Command | Result |
| --- | --- |
| `python -m pytest -q tests/test_instructor_routing.py` (RED, before implementation) | `12 failed, 3 passed, 17 warnings in 14.32s` |
| `python -m pytest -q tests/test_instructor_routing.py` (GREEN, after implementation) | `15 passed, 17 warnings in 11.67s` |
| `python -m pytest -q tests/test_instructor_routing.py tests/test_tickets.py tests/test_integrations.py tests/test_notifications.py tests/test_leave.py` | `57 passed, 17 warnings in 53.54s` |
| `python -m pytest -q` | `202 passed, 17 warnings in 142.21s (0:02:22)` — **historical Phase 7 run only**, superseded by the final `229 passed` run in §2.1. |
| `python -m alembic heads` | `feedf21773e1 (head)` — no migration added |
| `npm run typecheck` | Passed |
| `npm run lint` | Passed |
| `npm run build` | Passed |

Coverage includes eligible selection, active-leave exclusion, the exclusive leave end boundary,
inactive/HOD/admin exclusion, workload ranking, stable tie-breaks, assignment/status history, audit
events, exactly-once instructor notification, no-eligible-instructor fallback, manual override,
unauthorized assignment rejection, explicit-department behavior, email/WhatsApp intake, and
manual-assignment auto-reply preservation. Routing is deterministic and staff-only: HOD/admin
accounts are never auto-assigned, active `InstructorLeave` windows are excluded, and all overrides
are audited. These tests are included in the final 229-test suite.

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

`npm run build` compiled successfully, passed lint and type validation, and generated
12/12 static pages on Next.js 16.4.6 with webpack. The ticket detail route `ƒ /tickets/[ticketId]` was built at 19.6 kB with a
179 kB first load. Phase 7 routes remain present. Files added/changed for this UI are
`src/lib/api/types.ts`, `src/lib/api/endpoints.ts`, `src/components/tickets/TicketAttachments.tsx`
(new), `src/components/tickets/TicketDetail.tsx`, and `src/app/api/backend/[...path]/route.ts`.
The BFF now forwards multipart uploads as raw bytes so binary files are not corrupted by UTF-8 text
decoding. No live authenticated upload was exercised against a running backend; the backend path is
covered by the API tests in §2.

### 4.1 Browser E2E and accessibility (2026-11-23)

The earlier statement that no e2e/accessibility suite existed is superseded. The working-tree
Playwright + axe suite lives in `frontend-next/e2e/` (`auth.spec.ts`, `tickets.spec.ts`,
`a11y.spec.ts`, `helpers.ts`). At the time of that historical reconciliation it was uncommitted;
the final repository state is now `origin/main` `2cb5595...` with a clean working tree (§10).

```powershell
cd frontend-next
npm run test:e2e
```

- `pretest` ran `next build` successfully.
- `12 passed in 2.0m` in the final rerun (the earlier `11 passed (1.3m)` result is historical).
- axe reported **no serious or critical violations** on the login page, the student workspace and
  ticket detail.
- `useTicketStatusPolling.test.tsx` (Vitest) covers the polling hook's change detection; the E2E
  ticket spec also exercises a status-change/polling case.
- This is local verification only; no hosted/production browser run was performed.

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
| Full backend suite | `.\.venv\Scripts\python.exe -m pytest -q` | Historical release-hardening run: `187 passed, 17 warnings in 294.79s`. The FINAL full rerun is `229 passed, 17 warnings in 410.30s (0:06:50)` (§2.1). |
| Frontend static checks | `npm run typecheck`; `npm run lint`; `npm run build` | All exit 0; `next build --webpack` on Next.js 16.4.6 generated 12/12 static pages. |
| Compose validation | `docker compose -f docker-compose.db.yml config --quiet`; `docker compose -f docker-compose.yml config --quiet` | Both exit 0; `docker build --check .` reported no warnings. |
| Redacted current-tree secret scan | Python scanner over 310 non-generated text files; pattern classes and locations only, no values | Three findings, all in `backend/.env`: `OPENAI_API_KEY` at line 42 (key pattern plus non-placeholder assignment) and `BYOK_ENCRYPTION_KEY` at line 51 (Fernet-key shape). Test fixtures and `.env.example` placeholders were classified as informational. No secret value was printed. |
| Git history / staged / untracked audit | `git rev-parse --is-inside-work-tree`; `git status --short --untracked-files=all`; read-only scans | Git repository is present. The 385 tracked files were audited read-only (306 text files and 1 PDF); PASS for secrets, credentials, PII, and artifacts. Zero files are staged and `backend/.env` is ignored. At that historical point no commit/remote existed; current release-evidence commit is `2cb5595ee7a38c85c63223079dc9d17a290ed089` with a clean tree (§10). |
| Backend image secret/content audit | `docker run --rm --entrypoint sh smartquery-backend:release-audit -c 'find ...'` and `grep -RIl ...` | No `.env*`, key/certificate files, database files, logs, backups, temp files, generated reports, attachment files, tests, `.pyc` files, or secret-pattern matches. Runtime user `app`, workdir `/app`. |
| Frontend image secret/content audit | `docker run --rm --entrypoint sh smartquery-frontend:release-audit -c 'find ...'` and `grep -RIl ...` | No `.env*`, key/certificate files, npmrc, logs, backups, temp files, or secret-pattern matches. Runtime user `nextjs`, workdir `/app`. |

The two `backend/.env` findings are treated as compromised. They were not read into output, copied, changed, rotated, or deleted by this audit. Rotation remains an operator action. The broader redacted secret audit recorded in `docs/evidence/secret_audit.json` supersedes the earlier scan counts; its summary is in §6.1.

## 6.1 Requirement-area verification added 2026-11-23

These items reconcile stale claims against the local evidence. The historical
`FAIL — DO NOT DEPLOY` governance decision they refer to has been superseded by the 2026-11-24
final verification (§10) and `docs/RELEASE_READINESS.md`.

| Area | Verified local evidence | Caveat |
| --- | --- | --- |
| Full backend suite | `229 passed, 17 warnings in 410.30s (0:06:50)` from `backend/` (§2.1); focused malware/attachment run `10 passed, 17 warnings in 7.63s`. | Warnings are pre-existing LangSmith deprecations. |
| FR-04b / FR-13 instructor routing | `tests/test_instructor_routing.py`: deterministic, staff-only selection; active `InstructorLeave` windows excluded; HOD/admin never auto-assigned; audited overrides. Included in final suite (§2.5). | No in-app leave-approval workflow. |
| FR-06 status tracking | `GET /api/v1/tickets/{id}/updates` returns an ETag/`304 Not Modified` snapshot; frontend `useTicketStatusPolling` hook and `useTicketStatusPolling.test.tsx`; E2E polling case (§4.1). | **Polling only — not SSE/WebSocket push.** |
| FR-07 escalation | Secret-protected `POST /api/v1/tickets/escalation/sweep` with `X-Cron-Secret` constant-time check, tests in `tests/test_escalation_serverless.py`. The schedule is the valid daily `0 0 * * *` in `backend/vercel.json` (Vercel Hobby allows at most once/day). | **Schedule existence verified; hosted cron invocation, escalation effect, and hosted secret configuration NOT VERIFIED.** |
| FR-14 auth audit | `tests/test_auth_audit.py` covers password register/login success and failure audit events. | No password or secret is written to audit rows. |
| Token expiry | `tests/test_token_expiry.py` asserts the production default of 60 minutes. | 1440-minute lifetime is test-only, not a production setting. |
| Backup/restore | `docs/evidence/backup_restore_rehearsal.json`: status `PASS`; disposable `postgres:16-alpine` at `127.0.0.1:55432`; schema hash `ed7d1ab744886956c3e35ddde4674a05b01da26ef8313199b2c741e35917664b` and record hash `00e07e9f6182a27c59db5e2b9b0d51055011c13029485c4647b9ba4cc994d419` matched after restore; stale row count 1 → 0; container removed. | Production/DB volume untouched. Local rehearsal only. |
| Malware scanning | `docs/evidence/malware_scan_verification.json`: `PASS_LOCAL_INTEGRATION_ONLY`; real `clamav/clamav:stable` digest `sha256:64e30c0bf976198024deb3dc6d5cfe2485fb969c0f73549ba0fdb364b9469614` gave clean `OK`/exit 0 and in-container base64 EICAR `Eicar-Test-Signature FOUND`/exit 1; fail-closed behavior covered by tests. | A Windows-mounted EICAR fixture failed and is **not** claimed as a pass. `MALWARE_SCAN_ENABLED=false` by default; not deployed. |
| Secret audit | `docs/evidence/secret_audit.json` + `docs/SECRET_AUDIT_REMEDIATION_PLAN.md`: 385 tracked files, 17 workspace potential secrets, 12 git-history potential secrets, 453 docker-image potential secrets, 4 current-local-env matches. | No value printed/copied; **no rotation or revocation performed**. |
| npm audit | Final: `docs/evidence/npm_audit_final_2026-11-24.json` and `docs/evidence/npm_audit_prod_final_2026-11-24.json` report **0 vulnerabilities**. The 6-package 2026-11-23 result (`npm_audit_summary.json`) is historical/superseded. | The Next.js 16.4.6, Zod 4.6.7 and Vitest 4.1.12 upgrades were applied and re-verified (§6.4). |
| Registry | Current Docker Hub repository `raphicsdigitalsolutions/smart-query-system`: `latest` and `v1.0.0` both publish `sha256:2cf0a5dea54dffd643abf29a1fa7b72966899ff7235350b95fe1da793c9c2177`, matching local RepoDigests; anonymous pull/manifest verified. Historical GHCR existence/pull check used a different digest. | GHCR publication of current changes still lacks `write:packages`; no GHCR registry or image was modified (§6.2, §10). |

### 6.2 Dependency and registry reconciliation (2026-11-23 — historical/superseded)

These findings were superseded by the applied upgrades and the Docker Hub release in §6.4/§10.
Commands executed from `frontend-next/` (using `cmd /c` for reliable JSON redirection on Windows):

```powershell
cmd /c "npm audit --json > ..\docs\evidence\npm_audit_full_2026-11-23.json"
cmd /c "npm audit --omit=dev --json > ..\docs\evidence\npm_audit_prod_2026-11-23.json"
npm explain next postcss vitest @vitest/mocker tinypool zod | Out-File -FilePath ..\docs\evidence\npm_dependency_paths_2026-11-23.txt -Encoding utf8
```

Results: full audit `6` vulnerable packages (2 moderate, 2 high, 2 critical); production-only audit
`3` (`next`, `postcss`, `zod`). Installed versions: `next@15.5.29` with nested
`postcss@8.4.31`, `zod@3.25.76`, `vitest@3.2.4`, `@vitest/mocker@3.2.4`, `tinypool@1.1.1`.
Fix targets: `next@16.4.6` (pins `postcss@8.5.23`), `zod@4.6.7`, `vitest@4.1.12` (resolves the
mocker/tinypool findings). None was applied; approval is required. Node was `v22.23.2`, npm `10.9.0`.

Read-only GHCR evidence (`docs/evidence/ghcr_readonly_investigation.json`) used an anonymous token,
manifest/blob requests and `docker buildx imagetools inspect`: challenge `401`, token `200`,
manifest `200`, OCI index digest `sha256:417e017081a460adfe310236e13b3e117cb972c11c5c93370968aa866a2b0f0f`,
matching the recorded and local digests. No token value was stored; no push or registry write was
attempted. This supersedes the earlier "image URL unavailable" wording for that GHCR package only;
it is a historical read-only check and does not describe the current Docker Hub release (§10), nor
does it resolve the `write:packages` blocker for publishing changes to GHCR.

### 6.3 Escalation history & notification verification (2026-11-23)

- Full backend suite: `229 passed, 17 warnings in 410.30s (0:06:50)` in the final rerun (`.\.venv\Scripts\python.exe -m pytest -q`).
- Focused escalation/ticket/notification/audit run: `42 passed, 17 warnings in 70.95s` (`tests/test_escalation.py`, `tests/test_escalation_serverless.py`, `tests/test_tickets.py`, `tests/test_ticket_updates.py`, `tests/test_notifications.py`, `tests/test_audit.py`).
- Focused AI consistency/agents/BYOK/knowledge/evaluation run: `50 passed, 17 warnings in 32.74s`.
- Focused security, auth, attachment/malware, and serverless cron run: `64 passed, 17 warnings in 27.06s` (`tests/test_release_hardening.py`, `tests/test_byok_rotation.py`, `tests/test_auth.py`, `tests/test_auth_audit.py`, `tests/test_attachments.py`, `tests/test_malware_scan_service.py`, `tests/test_attachment_malware.py`, `tests/test_escalation_serverless.py`, `tests/test_token_expiry.py`).
- Re-verified disposable backup/restore rehearsal (`$env:DEBUG='false'; .\scripts\backup_restore_rehearsal.ps1` at `2026-11-23T16:57:24Z`): status `PASS`, schema hash `ed7d1ab744886956c3e35ddde4674a05b01da26ef8313199b2c741e35917664b`, record hash `00e07e9f6182a27c59db5e2b9b0d51055011c13029485c4647b9ba4cc994d419`, stale row count `1 -> 0`, `production_touched: false`.
- Re-verified local ClamAV container (`clamav/clamav:stable`, `ClamAV 1.5.5/28191`): clean fixture `OK` (exit `0`), EICAR fixture `Eicar-Test-Signature FOUND` (exit `1`).
- Read-only GHCR verification (`docker buildx imagetools inspect ghcr.io/raphicsdigitalsolutions/smart-query-system:latest`): digest `sha256:417e017081a460adfe310236e13b3e117cb972c11c5c93370968aa866a2b0f0f` matches `docs/evidence/ghcr_readonly_investigation.json`.
- Frontend static checks & E2E: `npm run typecheck`, `npm run lint` (`0` errors/warnings), `npm run test` (`3 passed` Vitest), `npm run build` (`12/12` pages, Next.js 16.4.6 webpack), and `npm run test:e2e` (`12 passed in 2.0m` including Playwright escalation/de-escalation recorded history and staff notifications).

## 7. Explicitly blocked checks

| Check | Why it was not performed |
| --- | --- |
| Live OpenAI key validation / live evaluation | Requires an explicitly configured personal OpenAI key. Production has no global fallback. |
| Live Google OAuth sign-in | Requires a real Google Cloud OAuth client ID and registered JavaScript origin. |
| Live SMTP delivery | Requires real SMTP credentials and a verified `MAIL_FROM` domain. |
| Live Meta WhatsApp send and webhook registration | Requires a real Meta Cloud API token, phone number ID, and webhook verification token. |
| Formal production/public release approval | Not granted. The hackathon deployment and technical release artifacts are verified, but institutional/governance sign-off, hosted monitoring and retention remain open. Current status is **TECHNICAL RELEASE COMPLETE; FORMAL APPROVAL PENDING** (§10). |
| Hosted escalation cron invocation | The daily `0 0 * * *` schedule is verified in the live deployment; the actual hosted invocation, escalation effect, and hosted `ESCALATION_CRON_SECRET` configuration were not performed or verified (§6.1, §10). |
| GHCR publication of current local changes | Blocked by missing `write:packages`; no registry was modified. Existing package existence/pull is verified read-only (§6.2). |
| Secret rotation/revocation | Not performed; 4 current-local-env matches require owner action (§6.1). |
| Browser E2E/accessibility on hosted deployment | Local working-tree Playwright + axe suite passed (§4.1); no hosted/production browser run was performed. |

## 8. Explicit pending implementation items

These items are tracked in `docs/MASTER_REQUIREMENTS_CHECKLIST.md` Section L and are not claimed as
complete:

- Instructor-level automatic assignment: implemented and verified under FR-04b/FR-13 (§2.5, §6.1).
- FR-06: conditional ETag/304 polling plus `useTicketStatusPolling` and an E2E case are local-verified
  (§4.1, §6.1). True SSE/WebSocket push is not implemented and is not claimed.
- FR-07: cron trigger code/config is local-verified; live hosted cron execution is NOT VERIFIED
  (§6.1).
- FR-14: password register/login success and failure audit events are implemented and local-verified
  (§6.1).
- Still pending: formal institutional approval, live provider verification, operator secret
  review/rotation, Netlify deploy/source confirmation by the site owner, hosted cron invocation
  verification, optional GHCR `write:packages` publication, and a real labelled evaluation dataset.
  The Next.js/Zod/Vitest upgrades are applied and verified. See `docs/FINAL_RELEASE_BLOCKERS.md`,
  `docs/OPERATOR_ACTION_CHECKLIST.md` and `docs/RELEASE_READINESS.md` for operator steps.

## 9. Reproduction order

1. Copy the example env files documented in `README.md`; fill secrets only in local/operator stores.
2. From `backend/`, run `pip install -r requirements.txt`, then the Python commands in §2.
3. From `frontend-next/`, run `npm ci`, then the commands in §4.
4. From the repository root, run the Compose and build commands in §5.
5. Use `docs/DEPLOYMENT_GUIDE.md` for provider setup, backup, restore, rollback, and health checks.

## 6.4 Final Dependency Remediation & Re-verification (2026-11-24)

All 6 previously open frontend dependency vulnerabilities (`next`/`postcss`, `zod`, `vitest`, `@vitest/mocker`, `tinypool`) were resolved cleanly (`vitest@4.1.12` + `vite@^7.3.8` + `@testing-library/dom@^10.4.2`, `zod@4.6.7`, `next@16.4.6`, `eslint-config-next@16.4.6`), with compatibility updates to `useTicketStatusPolling.ts`, `api/auth/{login,register}/route.ts`, `eslint.config.mjs`, `layout.tsx`, and `package.json` (`next build --webpack`).

| Check | Exact Result (2026-11-24) | Notes |
| --- | --- | --- |
| `npm audit` & `npm audit --omit=dev` (`frontend-next/`) | **0 vulnerabilities** (`743` total / `211` prod) | Final evidence: `docs/evidence/npm_audit_final_2026-11-24.json`, `docs/evidence/npm_audit_prod_final_2026-11-24.json` (earlier `npm_audit_post_remediation*.json` captures are superseded). |
| `npm audit` (`frontend/`) | **0 vulnerabilities** | Legacy Vite SPA preserved cleanly. |
| `npm run typecheck` / `npm run lint` / `npm run test` | **PASS** (0 TS/ESLint errors; **3 passed** Vitest 4.1.12) | Clean across all updated routes and ESLint 9 flat config. |
| `npm run build` (`next build --webpack` v16.4.6) | **PASS** (12/12 static pages) | Next 16 default Turbopack hit `TurbopackInternalError` spawning the PostCSS worker on Windows/OneDrive; `build` and `pretest:e2e` pin `--webpack`, which passes locally and inside Docker (`node:20-alpine`). |
| `npm run test:e2e` (Playwright + Axe) | **12 passed in 2.0m** | Zero serious/critical axe violations (`docs/evidence/e2e_axe_result.json`); verified with host loopback access (`BypassSandbox: true`; Windows AppContainer sandbox blocked `127.0.0.1`). |
| `backend\.venv\Scripts\python.exe -m pytest -q` | **229 passed, 17 warnings in 410.30s (0:06:50)** — final rerun | 0 failed/errors (`docs/evidence/final_backend_test.json`). Run with `DEBUG=false` and host loopback access (Windows sandbox blocked `ProactorEventLoop._make_self_pipe` `socketpair()` inside `TestClient`). |
| `scripts/backup_restore_rehearsal.ps1` | **PASS** | Clean Alembic upgrade `44273a775ed8 -> feedf21773e1` + `pg_dump`/`pg_restore` hash match on disposable `postgres:16-alpine`. |
| `docker build` (`backend` & `frontend-next`) | **PASS** | Built `smartquery-backend:submission-audit` and `smartquery-frontend:submission-audit` cleanly. |
| Isolated Container Health & BFF Smoke | **PASS** | Production-mode scratch stack (`postgres:16-alpine` + `smartquery-backend` + `smartquery-frontend`): `postgres_ready=True`, `backend_health=healthy`, `frontend_health=healthy`, `/api/health` 200, `/login` 200, `/api/auth/session` 200, unauthenticated `/api/backend/auth/me` 401; scratch resources removed. |
| Combined Supervisor Image (`Dockerfile`) & Docker Hub Publish | **PASS** | Built single unified image (`python:3.11-slim` + `node:20-slim` + Supervisor, non-root UID 10001, zero `.env`/key files/dev tools/playwright), verified healthy container with Supervisor backend+frontend RUNNING and backend health/login/api-health/session all HTTP 200 using disposable SQLite with email/WhatsApp/worker disabled; published `raphicsdigitalsolutions/smart-query-system:latest` and `:v1.0.0`, both at digest `sha256:2cf0a5dea54dffd643abf29a1fa7b72966899ff7235350b95fe1da793c9c2177`, matching local RepoDigests. Anonymous pull (temporary empty Docker config, exit 0) and manifest HTTP 200 verified. Pattern matches in the image were Next.js docs/library strings only. The older `sha256:e9ed70810b3f9e5c6bb5ee1e7fb83847acb423c18a2bb506d9e83a5368450430` is stale. |

---

## 10. Final release verification (2026-11-24)

**Status: TECHNICAL RELEASE COMPLETE; FORMAL APPROVAL PENDING.** This section supersedes the
historical `FAIL — DO NOT DEPLOY` current-state verdicts in earlier sections.

| Area | Verified result | Evidence / caveat |
| --- | --- | --- |
| Git | release-evidence commit `2cb5595ee7a38c85c63223079dc9d17a290ed089`; chain `b51dd31` → `7ad663e` (daily cron + Phase 1/2 evidence) → `eb30f92` (Docker Hub evidence) → `2cb5595` (live verification evidence); clean working tree after that commit. | `docs/evidence/phase1_release_audit_2026-11-24.json`, `phase2_quality_verification_2026-11-24.json` |
| Infrastructure config | `docker compose -f docker-compose.db.yml config --quiet` and `docker compose -f docker-compose.yml config --quiet` PASS; `docker build --check .` no warnings; Alembic heads/current `feedf21773e1`, `alembic check` clean. | Local/config verification only. |
| Vercel backend | Production deployment `dpl_CRo9kXq4CBL8p8oSaaAyKdSjNVoM` READY, target production, source CLI; aliases `smart-query-backend.vercel.app` and `smart-query-backend-inforaphicsdigital-8444.vercel.app`. Deployment metadata names commit `b51dd31` with a dirty CLI working tree; its deployed config already contained the daily cron. Current main's `backend/vercel.json` matches the deployed daily schedule. | `docs/evidence/phase5_live_verification_2026-11-24.json`. Hobby allows at most once/day; the old hourly `0 * * * *` was invalid. `vercel crons ls` shows exactly the one daily `0 0 * * *` entry for `/api/v1/tickets/escalation/sweep`. **Schedule existence only; hosted invocation/escalation effect NOT VERIFIED.** |
| Live backend smoke | `/health` 200 `healthy`; `/api/v1/status` 200 version `1.0.0`; `/api/v1/status/database` 200 `connected`; `/api/v1/departments` 401 unauthenticated (expected). | `docs/evidence/phase5_live_verification_2026-11-24.json`. |
| Netlify frontend | Public site `https://smart-query-routing-system.netlify.app`: `/` and `/api/health` both HTTP 200, `Server: Netlify`. | **Authenticated deploy state and source sync NOT VERIFIED**: no Netlify token configured, API returned 401 without credentials. Live HTML uses Turbopack chunks while current main builds with webpack after commit `75d6f16`; do not claim the live site is synced with current main. Recorded deploy ID `6b02db1360e3188d7f1074c6` could not be authenticated/confirmed. Owner must confirm the deploy and redeploy from GitHub `main` if needed; no redeploy was performed. |
| `release-v1` database | Read-only verification: database `neondb`, URL fingerprint `sha256_12 5d1fc726d19b`, host fingerprint `141f6064ec7f`, Alembic `feedf21773e1`, 17 public tables, `departments=4`, `users=0`, `tickets=0`, `writes_performed=false`. | `docs/evidence/release_v1_readonly_verification_2026-11-24.json`. Branch identity comes from the operator-provided, git-ignored `backend/.env.release_v1` **file name**. Vercel withholds sensitive `DATABASE_URL` values and Neon UI was unavailable, so **no direct Vercel-to-`.env` equality and no old production database state are claimed**. |
| Docker Hub | `raphicsdigitalsolutions/smart-query-system:latest` and `:v1.0.0` both publish `sha256:2cf0a5dea54dffd643abf29a1fa7b72966899ff7235350b95fe1da793c9c2177`, matching local RepoDigests; anonymous pull and manifest verified. | `docs/evidence/phase4_docker_hub_release_2026-11-24.json`, `docker_hub_anonymous_pull_2026-11-24.json`. |
| Final suites | Backend 229 passed / 17 warnings in 410.30s; Vitest 3 passed; typecheck/lint/build PASS (Next.js 16.4.6 webpack, 12/12 pages); Playwright + axe 12 passed in 2.0m, no serious/critical violations; `npm audit` and `npm audit --omit=dev` 0 vulnerabilities. | `final_backend_test.json`, `e2e_axe_result.json`, `npm_audit_final_2026-11-24.json`, `npm_audit_prod_final_2026-11-24.json`. |

**NOT VERIFIED / NOT CLAIMED:** Google OAuth, SMTP, Meta WhatsApp, real-user OpenAI BYOK, hosted
cron invocation (only the daily schedule is verified), university/institutional approval, hosted
restore or malware scanner, monitoring/retention, Netlify authenticated deploy state and source sync,
Vercel-to-`.env.release_v1` database equality, and old production database state. Formal production
approval is not granted; this is a live technical demonstration, not formal sign-off.

**Evidence index:** `docs/evidence/phase1_release_audit_2026-11-24.json`,
`phase2_quality_verification_2026-11-24.json`, `phase4_docker_hub_release_2026-11-24.json`,
`phase5_live_verification_2026-11-24.json`, `release_v1_readonly_verification_2026-11-24.json`,
`docker_hub_anonymous_pull_2026-11-24.json`, `final_backend_test.json`, `e2e_axe_result.json`,
`npm_audit_final_2026-11-24.json`, `npm_audit_prod_final_2026-11-24.json`.
