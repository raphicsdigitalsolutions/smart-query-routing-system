# API Reference (Phase 7 — FastAPI backend, Next.js BFF, BYOK AI)

Base URL (local): `http://localhost:8000`

All versioned routes are mounted under `http://localhost:8000/api/v1` (`API_V1_PREFIX`).
Unversioned status routes (`/`, `/health`) live at the base URL.

Interactive documentation: `http://localhost:8000/docs` (ReDoc: `/redoc`, machine-readable
OpenAPI: `/openapi.json`). The route table below was verified against the OpenAPI document
generated from `app.main` by the backend virtual environment.

Response shapes are explicit per endpoint. Collection endpoints return a wrapper with
`"success": true`, `items`, `total` and pagination fields. Single-resource and mutation
endpoints generally return the resource or mutation object directly; many of those models
carry their own `"success": true` field, while others (for example the knowledge document
response) do not. Every error response uses the shared envelope
`{"success": false, "error", "detail", "code"}` where `detail` may be `null` and `code` may
be `null`.

This document describes the implemented HTTP contract. It does **not** claim that live
Google, SMTP, WhatsApp or OpenAI calls have been verified with real credentials; those flows
are environment/credential-dependent and are verified in automated tests with mocked or
local providers. No build numbers or test results are asserted here.

---

## Route index

All paths below are relative to `/api/v1` unless marked *(unversioned)*.

| Group | Methods & paths | Authorization |
| --- | --- | --- |
| Auth (legacy) | `POST /auth/register`, `POST /auth/login`, `GET /auth/me` | Public / authenticated |
| Auth (Google) | `POST /auth/google` | Public; requires Google OAuth config |
| Status | `GET /status`, `GET /status/database`; *(unversioned)* `GET /`, `GET /health` | Public |
| Users | `GET /users/assignable` | Staff/HOD/admin |
| Departments | `GET /departments`, `POST /departments`, `PATCH /departments/{department_id}` | Authenticated / admin |
| Tickets | `POST /tickets`, `GET /tickets`, `GET /tickets/{ticket_id}`, `PATCH /tickets/{ticket_id}`, `POST /tickets/{ticket_id}/assign`, `GET /tickets/{ticket_id}/messages`, `POST /tickets/{ticket_id}/messages`, `GET /tickets/{ticket_id}/attachments`, `POST /tickets/{ticket_id}/attachments`, `GET /tickets/{ticket_id}/history` | Role-scoped (see Tickets) |
| AI | `POST /ai/tickets/{ticket_id}/analyze`, `GET /ai/tickets/{ticket_id}/analysis`, `POST /ai/tickets/{ticket_id}/draft`, `POST /ai/tickets/{ticket_id}/approve-draft` | Staff/HOD/admin + BYOK key |
| Settings (BYOK) | `GET /settings/api-keys`, `PUT /settings/api-keys`, `POST /settings/api-keys/validate`, `DELETE /settings/api-keys` | Authenticated, per-user |
| Knowledge | `GET /knowledge`, `POST /knowledge`, `GET /knowledge/{document_id}`, `GET /knowledge/{document_id}/versions`, `PATCH /knowledge/{document_id}`, `DELETE /knowledge/{document_id}` | Staff+ read / HOD+ manage |
| Analytics | `GET /analytics/overview` | Staff/HOD/admin |
| Announcements | `GET /announcements`, `POST /announcements`, `PATCH /announcements/{announcement_id}`, `DELETE /announcements/{announcement_id}` | Authenticated read / admin manage |
| Leave | `GET /leave`, `POST /leave`, `PATCH /leave/{leave_id}`, `DELETE /leave/{leave_id}` | Staff/HOD/admin |
| Audit | `GET /audit` | Admin only |
| Reports | `GET /reports/tickets.pdf`, `GET /reports/tickets.xlsx` | Staff/HOD/admin |
| Notifications | `GET /notifications`, `POST /notifications/{notification_id}/read` | Authenticated, recipient-scoped |
| Integrations | `GET /integrations/status`, `GET /integrations/whatsapp/webhook`, `POST /integrations/email/inbound`, `POST /integrations/whatsapp/inbound` | Public status / Meta verification handshake / token-gated intake |
| Operations | `POST /tickets/escalation/run` | Admin only |

---

## Application boundary: Next.js BFF (Phase 5, extended in Phase 7)

The Next.js app does not change the FastAPI contract above. It adds same-origin route handlers
under `frontend-next/src/app/api/` so the browser never receives the JWT or calls port 8000
directly. These paths are an application boundary, not a new public API version.

| BFF route | Purpose |
| --- | --- |
| `POST /api/auth/login` | Validates credentials through `/api/v1/auth/login`, sets HttpOnly `smartquery_session`, sets readable `smartquery_csrf`, returns user + CSRF token. |
| `POST /api/auth/register` | Creates a student through `/api/v1/auth/register` and establishes the same session cookies. |
| `POST /api/auth/google` | Exchanges a Google Identity Services credential through `/api/v1/auth/google` and establishes the same session cookies. |
| `POST /api/auth/logout` | Requires CSRF header/cookie match, clears both cookies. |
| `GET /api/auth/me` | Revalidates the session through `/api/v1/auth/me`; returns the current user or guest. |
| `GET /api/auth/session` | Session probe used by the client provider; bootstraps the CSRF cookie for guests. |
| `GET /api/health` | Proxies the unversioned FastAPI `/health` for the dashboard status card. |
| `GET /api/reports/{format}` | Streams `GET /api/v1/reports/tickets.pdf` or `tickets.xlsx` through the BFF; `format` is restricted to `pdf` or `xlsx`. Cookie-authenticated GET, so it is CSRF-safe. Returns binary `Content-Type`/`Content-Disposition` with `Cache-Control: no-store`. |
| `GET|POST|PATCH|DELETE|OPTIONS /api/backend/[...path]` | Proxies to `/api/v1/<path>` with the Bearer token attached server-side. Query strings are forwarded. |

BFF rules:

- `NEXT_PUBLIC_API_BASE_URL` defaults to `http://localhost:8000/api/v1`; optional `API_BASE_URL`
  overrides it server-side.
- The catch-all forwards `multipart/form-data` as raw bytes instead of decoding the body as text, so
  ticket attachment uploads are not corrupted in transit through the BFF. Standard CSRF rules still
  apply to `POST`.
- Unsafe BFF methods require `x-csrf-token` to equal the `smartquery_csrf` cookie. This includes
  logout; it was a real defect found and fixed during live validation. `GET`, `HEAD` and `OPTIONS`
  are treated as safe. A mismatch returns HTTP 403 with `code: "invalid_csrf"`.
- The JWT is always `HttpOnly`, `SameSite=Lax`, `Secure` in production, and never written to browser
  storage. The session lifetime matches the backend `expires_in` (60 minutes by default).
- Missing session or a FastAPI 401 returns a normalized 401 and clears the cookies. No backend
  secrets or JWTs are exposed to client code.
- Browser-side requests are same-origin, so FastAPI CORS does not need a port 3000 origin.
- A Google sign-in response must contain a `user` and either an `access_token` (preferred) or a
  `csrfToken`; otherwise the BFF returns HTTP 502. The backend always returns the standard login
  envelope, so the `access_token` path is used.

---

## Conventions

### Authentication (Bearer)

Protected endpoints require:

```http
Authorization: Bearer <access_token>
```

Tokens are returned by `POST /api/v1/auth/login` and `POST /api/v1/auth/google`, expire after
`ACCESS_TOKEN_EXPIRE_MINUTES` (60 by default), and are not refreshable. Missing, malformed,
expired or inactive-account tokens return HTTP 401 with one of these codes:

| Code | Meaning |
| --- | --- |
| `not_authenticated` | No Bearer credentials supplied |
| `invalid_token` | Malformed, wrong-type or revoked-by-inactivity token |
| `token_expired` | Token `exp` is in the past |

### Roles

| Role | Typical authority |
| --- | --- |
| `student` | Submit tickets, read own tickets/messages/notifications/announcements |
| `staff` | Assigned tickets, AI with personal key, own leave, knowledge read |
| `hod` | Department-scoped tickets, users, analytics, reports, knowledge management, leave |
| `admin` | All tickets and all administrative endpoints |

Role gates are enforced by dependencies in `app/api/deps.py`: `get_current_user`,
`require_staff_or_above` (staff/HOD/admin), `require_hod_or_admin`, `require_admin`, etc. A role
failure returns HTTP 403 with `code: "forbidden"`.

### CSRF and cookies

FastAPI itself is stateless and uses the Bearer token only; it does not read cookies. CSRF is a
BFF concern: the BFF stores the JWT in an HttpOnly cookie and exposes a separate readable CSRF
cookie. Unsafe methods must send `x-csrf-token` matching that cookie. Reports are downloaded with
a plain same-origin `GET`, so no CSRF header is needed. See the BFF rules above.

---

## Authentication endpoints

### `POST /api/v1/auth/register`

Public. Creates **only** an active `student`. Extra fields such as `role` or `department_id` are
ignored by validation, so role escalation is impossible through this endpoint.

```json
{
  "full_name": "Ada Student",
  "email": "ada@university.edu",
  "password": "a-strong-password-of-12-plus-chars"
}
```

HTTP 201 response:

```json
{
  "id": 1,
  "full_name": "Ada Student",
  "email": "ada@university.edu",
  "role": "student",
  "department_id": null,
  "is_active": true,
  "created_at": "2026-11-21T12:00:00Z"
}
```

Duplicate email returns HTTP 409 with `code: "duplicate_email"`. Passwords are hashed with Argon2id
and are never returned.

### `POST /api/v1/auth/login`

Public. Accepts `email` and `password`. Unknown emails, wrong passwords and inactive accounts all
return the same generic HTTP 401:

```json
{
  "success": false,
  "error": "Invalid email or password",
  "detail": null,
  "code": "invalid_credentials"
}
```

Success:

```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": 1,
    "full_name": "Ada Student",
    "email": "ada@university.edu",
    "role": "student",
    "department_id": null,
    "is_active": true,
    "created_at": "2026-11-21T12:00:00Z"
  }
}
```

### `POST /api/v1/auth/google`

Public. Passwordless Google sign-in. Requires `GOOGLE_OAUTH_ENABLED=true` and a configured
`GOOGLE_OAUTH_CLIENT_ID`; otherwise HTTP 503 with `code: "oauth_not_configured"`.

Request body:

```json
{ "credential": "eyJhbGciOiJSUzI1NiIsImtpZCI6..." }
```

`credential` is a Google ID token (1–8192 characters at the API; the BFF enforces 10–20000). The
backend verifies the RS256 signature against Google's JWKS, plus audience, issuer, expiry and
`email_verified`. A valid token is mapped to an existing user by verified email, or creates a new
`student` with a random unusable password. **An external token can never grant staff/HOD/admin
role.** The call is audited as `auth.google_login`.

Success returns HTTP 200 with the same shape as `/auth/login` (`access_token`, `token_type`,
`expires_in`, `user`). Error codes:

| HTTP | Code | Meaning |
| --- | --- | --- |
| 401 | `invalid_google_token` | Signature/claims/email verification failed |
| 401 | `inactive_account` | Matched account is inactive |
| 503 | `oauth_not_configured` | OAuth disabled or client id missing |
| 503 | `oauth_verification_unavailable` | Google JWKS could not be fetched |

Live verification requires real Google credentials and network access; this document does not
claim it was performed.

### `GET /api/v1/auth/me`

Requires authentication. Returns the `UserResponse` object for the current token (never the
password hash).

### Dev-only first admin provisioning

There is no HTTP endpoint for creating staff, HOD or admin users. From `backend/`:

```powershell
$env:ADMIN_PASSWORD = '<strong-password>'
python -m app.cli.provision_admin --email admin@university.edu
```

The CLI refuses `ENVIRONMENT=production`, refuses a second admin, accepts `ADMIN_EMAIL` instead of
`--email`, and uses a hidden prompt when `ADMIN_PASSWORD` is unset. No default credentials exist.

---

## Status endpoints

### `GET /` *(unversioned)*

```json
{
  "success": true,
  "message": "Smart Query Routing System API is running",
  "version": "1.0.0"
}
```

### `GET /health` *(unversioned)*

Liveness probe; does not query the database.

```json
{ "success": true, "status": "healthy" }
```

### `GET /api/v1/status`

```json
{
  "success": true,
  "service": "Smart Query Routing System",
  "version": "1.0.0",
  "api_prefix": "/api/v1"
}
```

### `GET /api/v1/status/database`

Readiness probe. HTTP 200 when connected:

```json
{ "success": true, "database": "connected" }
```

HTTP 503 when unavailable (never leaks connection details):

```json
{
  "success": false,
  "error": "Database is currently unavailable",
  "detail": null,
  "code": "database_unavailable"
}
```

---

## Departments

### `GET /api/v1/departments`

Requires authentication. Returns active departments for the ticket intake form.

```json
{ "success": true, "items": [{ "id": 1, "name": "Registry", "description": "Student records", "is_active": true }] }
```

### `POST /api/v1/departments`

Admin only. Body: `{ "name": "Student Housing", "description": "Accommodation support" }`.
Returns HTTP 201 and the department object.

### `PATCH /api/v1/departments/{department_id}`

Admin only. Any subset of `name`, `description`, `is_active`.

### `GET /api/v1/users/assignable`

Staff/HOD/admin only. Returns active users eligible for assignment. HODs see only their own
department; students receive HTTP 403.

```json
{
  "success": true,
  "items": [
    { "id": 2, "full_name": "Grace Staff", "email": "grace@university.edu", "role": "staff", "department_id": 1 }
  ]
}
```

---

## Tickets

### Roles and visibility

| Role | Can view |
| --- | --- |
| `student` | Only tickets they submitted |
| `staff` | Only tickets assigned to them |
| `hod` | Only tickets in their department |
| `admin` | All tickets |

An unauthorized or guessed ticket ID returns HTTP 404 with `code: "not_found"` so ticket existence
is not disclosed. A visible ticket can still return HTTP 403 for a forbidden action.

### `POST /api/v1/tickets`

Students only. Body:

```json
{
  "subject": "Transcript request",
  "description": "I need an official transcript for graduation.",
  "department_id": 1,
  "category": "Records",
  "priority": "normal"
}
```

`auto_route` (bool, default `false`) and `channel` (`web` by default; `email`/`whatsapp` are set by
the inbound adapters and passed explicitly) are also accepted. Priority values: `low`, `normal`,
`high`, `urgent`. HTTP 201 returns the ticket with a unique `public_reference` such as
`TKT-4AF29C10`, `status: "new"`
and `is_escalated: false`. A `ticket.created` status history row, audit row and notification are
written in the same flow.

### `GET /api/v1/tickets`

Requires authentication. Role scoping is applied automatically.

| Query parameter | Type | Notes |
| --- | --- | --- |
| `skip` | int ≥ 0 | Pagination offset |
| `limit` | int 1–100 | Page size |
| `status` | enum | `new`, `assigned`, `in_progress`, `waiting_for_student`, `resolved`, `closed` |
| `priority` | enum | `low`, `normal`, `high`, `urgent` |
| `department_id` | int > 0 | Filter by department |
| `assignee_id` | int > 0 | Filter by assignee |
| `escalated` | bool | `true` / `false` |
| `search` | string ≤ 120 | Matches subject/description |

```json
{
  "success": true,
  "items": [{ "id": 1, "public_reference": "TKT-4AF29C10", "subject": "Transcript request", "status": "new", "priority": "normal", "is_escalated": false, "student_id": 1, "assigned_to": null, "department_id": 1, "department_name": "Registry", "created_at": "2026-11-21T12:00:00Z", "updated_at": "2026-11-21T12:00:00Z" }],
  "total": 1,
  "skip": 0,
  "limit": 20
}
```

### `GET /api/v1/tickets/{ticket_id}`

Requires visibility. Returns the full ticket object with student, assignee and department names.

### `PATCH /api/v1/tickets/{ticket_id}`

Requires visibility and role permission. Accepted fields: `subject`, `description`, `priority`,
`status`, `is_escalated`, `department_id`.

- Students: forbidden (403).
- Staff: may change only `status` on tickets assigned to them.
- HOD: may change `status`, `priority` and `is_escalated` in their department.
- Admin: may change all fields on any ticket.

Status transitions are validated:

```text
new                  -> assigned | in_progress | closed
assigned             -> in_progress | waiting_for_student | resolved | new
in_progress          -> waiting_for_student | resolved | assigned
waiting_for_student  -> in_progress | resolved | closed
resolved             -> closed | in_progress
closed               -> (terminal)
```

Staff additionally cannot use transitions back to `new`. An invalid transition returns HTTP 409
with `code: "invalid_status_transition"`. Each change appends `ticket_status_history` and an audit
row. Escalation and administrative overrides are also audited.

Response:

```json
{ "success": true, "ticket": { "...": "updated ticket" }, "message": null }
```

### `POST /api/v1/tickets/{ticket_id}/assign`

HOD or admin only. Body: `{ "assignee_id": 2 }` or `{ "assignee_id": null }` to unassign.
HODs may assign only staff/HOD/admin users in their own department; admins may assign any eligible
user. Assignment appends a history row and automatically moves a `new` ticket to `assigned`
(unassignment moves an `assigned` ticket back to `new`). Assigning a student is rejected with
`code: "invalid_assignee"`.

Response uses the same wrapper as `PATCH`:

```json
{ "success": true, "ticket": { "...": "updated ticket" }, "message": "Assignment updated" }
```

### `GET /api/v1/tickets/{ticket_id}/messages`

Requires visibility. Returns public messages plus internal notes for staff/HOD/admin. Students never
receive `is_internal: true` rows.

```json
{
  "success": true,
  "items": [
    { "id": 1, "ticket_id": 1, "sender_id": 2, "sender_name": "Grace Staff", "message_body": "Please upload your transcript.", "is_internal": false, "created_at": "2026-11-21T12:05:00Z" }
  ],
  "total": 1
}
```

### `POST /api/v1/tickets/{ticket_id}/messages`

Requires visibility. Body:

```json
{ "message_body": "Please upload your transcript.", "is_internal": false }
```

Students cannot set `is_internal: true` (403). Messages on a `closed` ticket are rejected with HTTP
409 and `code: "ticket_closed"`. Every message is audited. **Internal notes do not generate any
notification row or outward delivery**; only public replies notify participants. The first public
staff reply also starts the `first_response_at` clock used by analytics/SLA.

### `POST /api/v1/tickets/{ticket_id}/attachments`

Requires ticket visibility. This is a `multipart/form-data` endpoint:

| Field | Type | Notes |
| --- | --- | --- |
| `file` | file | Required. Extension and content signature are validated against `ALLOWED_UPLOAD_TYPES` (default `pdf,txt,md`, 5 MiB default). |
| `message_body` | form string | Optional; defaults to `Attachment: <filename>`. |
| `is_internal` | form boolean | Optional; students cannot set it true. |

Bytes are written atomically to `ATTACHMENT_STORAGE_DIR`, outside the web root and the database; only
safe metadata and a SHA-256 checksum are persisted in `message_attachments`. The endpoint creates the
associated message and one `attachment.uploaded` audit row in the same transaction. Public uploads
follow the normal public-reply notification rules; internal uploads create no notifications. Invalid
extensions, mismatched content, empty files, or oversized files return 413/415/422 and no message or
file is retained. The response contains only safe metadata (no disk path or checksum):

```json
{ "id": 1, "message_id": 9, "file_name": "notes.txt", "content_type": "text/plain", "size_bytes": 28, "created_at": "2026-11-21T12:10:00Z" }
```

### `GET /api/v1/tickets/{ticket_id}/attachments`

Requires ticket visibility. Returns attachment metadata only for messages the caller is allowed to see,
so a student never receives an internal note's attachment metadata.

```json
{ "success": true, "items": [{ "...": "attachment metadata" }], "total": 1 }
```

### `GET /api/v1/tickets/{ticket_id}/history`

Requires visibility. Returns status and assignment timelines in ascending order:

```json
{
  "success": true,
  "status_changes": [
    { "id": 1, "from_status": null, "to_status": "new", "changed_by_id": 1, "note": "Ticket submitted", "created_at": "2026-11-21T12:00:00Z" }
  ],
  "assignments": []
}
```

---

## AI assistance (Phase 6 workflow, Phase 7 BYOK + rate limiting)

All four routes require an authenticated **`staff`, `hod` or `admin`** user. Students receive
HTTP 403 with `code: "forbidden"`. The ticket is then loaded through the same
`get_accessible_ticket()` service used by the ticket API, so an invisible ticket returns HTTP 404
with `code: "not_found"` rather than revealing its existence. The Next.js BFF proxies these paths
unchanged; no OpenAI key or provider response body is ever returned to the browser.

Two Phase 7 controls apply to every run endpoint (`analyze`, `draft`, and `approve-draft` only
through the persisted-run checks):

1. **BYOK-only in real runs.** A real analysis resolves the requesting user's personal OpenAI key.
   See [BYOK failure behavior](#byok-failure-behavior) below.
2. **Durable per-user rate limit.** `_enforce_rate_limit()` counts the caller's persisted `AgentRun`
   rows created in the last 60 seconds. At or above `AI_RATE_LIMIT_PER_MINUTE` (default 20) it
   rejects with HTTP 429 and `code: "ai_rate_limited"` **before** creating a provider call. A
   successful or failed persisted analysis writes an `AgentRun`, so the counter is durable across
   processes and restarts.

Each successful analysis response uses this envelope (metadata fields may be `null`):

```json
{
  "success": true,
  "id": 12,
  "ticket_id": 7,
  "version": 2,
  "status": "completed",
  "is_current": true,
  "classification": {
    "intent": "request_password_reset_help",
    "category": "account_access",
    "urgency": "normal",
    "language": "en",
    "entities": ["password"],
    "confidence": 0.82,
    "rationale": "The query asks about account access and password reset."
  },
  "priority_recommendation": "normal",
  "department_recommendation": {
    "department_id": 1,
    "department_name": "Registry",
    "confidence": 0.76,
    "reason": "Account access requests fit this department.",
    "source": "model"
  },
  "staff_recommendation": null,
  "knowledge_sources": [],
  "no_evidence": true,
  "draft": {
    "body": "Thanks for contacting us. I could not verify an answer...",
    "language": "en",
    "confidence": 0.0,
    "source_ids": [],
    "needs_staff_review": true
  },
  "validation": {
    "passed": true,
    "issues": [],
    "overall_confidence": 0.76,
    "checked_at": "2026-11-21T21:00:00Z"
  },
  "confidence": 0.76,
  "abstention_reason": "No approved knowledge source matched this query.",
  "error": null,
  "execution_metadata": [],
  "approved_message_id": null,
  "approved_at": null,
  "created_at": "2026-11-21T21:00:00Z"
}
```

`error` is non-null only for a persisted failed run and contains only a stable `code` and fixed
sanitized `message`. Execution metadata contains node/status/duration/attempt/model fields, never a
prompt or raw provider response. **AI retrieval reads only approved, active knowledge documents**
(and respects department scope for non-admins); unapproved or deactivated documents are never
seen by the research node, and an empty repository causes an abstention rather than an invented
answer. Student name/email and internal notes are excluded from the prompt state.

### `POST /api/v1/ai/tickets/{ticket_id}/analyze`

Runs one bounded LangGraph analysis, persists a new version and returns HTTP 201. It does **not**
assign, change status, send email or publish a message. The graph is
`classification -> routing -> knowledge_research -> response_drafting -> validation`.

### `GET /api/v1/ai/tickets/{ticket_id}/analysis`

Returns the current analysis for a visible ticket. HTTP 404 with
`code: "ai_analysis_not_found"` means no analysis has been stored yet.

### `POST /api/v1/ai/tickets/{ticket_id}/draft`

Regenerates the analysis/draft using the same bounded workflow and returns HTTP 201 with a new
version. The frontend labels this action “Regenerate draft”; the previous version is retained but
no longer current.

### `POST /api/v1/ai/tickets/{ticket_id}/approve-draft`

Explicit human approval. Publishes the current draft as a **public** message through
`create_message()` and returns:

```json
{
  "success": true,
  "analysis_id": 12,
  "message": {
    "id": 31,
    "ticket_id": 7,
    "sender_id": 2,
    "sender_name": "Grace Staff",
    "message_body": "The approved draft text...",
    "is_internal": false,
    "created_at": "2026-11-21T21:05:00Z"
  },
  "already_approved": false
}
```

Repeat calls return `already_approved: true` with the same message instead of publishing again.
A draft whose stored validation failed cannot be published (`ai_validation_failed`, 409). Other
errors: `ai_no_draft` (409) when no current draft exists, `ticket_closed` (409) via the existing
message service, and the standard ticket visibility errors. Approval is audited and sends a public
reply notification; unapproved drafts never reach students.

### BYOK failure behavior

| Situation | Behavior |
| --- | --- |
| No personal key for the requesting user | Real AI runs raise HTTP **402** with `code: "ai_personal_key_required"`. No AI call is made. |
| Production global fallback | **Never used.** `ALLOW_GLOBAL_OPENAI_FALLBACK` is rejected at startup when `ENVIRONMENT=production`; even when the flag is set outside production, a personal key still takes precedence. |
| Development-only fallback | `settings.OPENAI_API_KEY` is consulted only when `ALLOW_GLOBAL_OPENAI_FALLBACK=true` **and** `ENVIRONMENT != "production"`. |
| Invalid/rejected provider key | Save/validate endpoints return HTTP 400 `invalid_api_key`; provider error text is deliberately discarded so key material cannot leak. |
| No configured key on validate/delete | HTTP 404 `api_key_not_found`. |
| Status endpoint | Returns metadata only (`status` is one of `not_configured`, `unvalidated`, `invalid`, `valid`), plus a masked `key_hint` and timestamps. The secret is never returned. |

**Missing-key UX contract (frontend):** the AI panel checks `ApiError.code === AI_MISSING_KEY_CODE`
where `AI_MISSING_KEY_CODE = 'ai_personal_key_required'`. On that code it
(1) shows an “Add your personal AI key” callout stating that no shared/administrator key is used,
with an **Open Settings** link to `/settings`; (2) disables Analyze, Regenerate and Approve
actions; and (3) emits a toast: “Add your personal AI key in Settings to use AI assistance.” The
same code can also arrive as `analysis.error.code` on a persisted failed run and is treated the
same way. On success the panel reports recommendations as non-binding and requires explicit human
approval before publishing.

### AI error codes

| HTTP | Code | Meaning |
| --- | --- | --- |
| 402 | `ai_personal_key_required` | No personal OpenAI key for this user; no production fallback. |
| 403 | `forbidden` | Caller is a student or otherwise lacks staff-level AI access. |
| 404 | `not_found` | Ticket is not visible to the caller. |
| 404 | `ai_analysis_not_found` | No current analysis exists for `GET`. |
| 409 | `ai_no_draft` / `ai_validation_failed` | No current draft exists, or the draft failed validation and cannot be published. |
| 429 | `ai_rate_limited` | Durable per-user run count (last 60 seconds) exceeded, or provider rate-limit category from the LLM wrapper. |
| 502 | `ai_invalid_response` / `ai_provider_error` / `ai_analysis_failed` | Invalid structured output or provider failure. |
| 503 | `ai_not_configured` / `ai_invalid_api_key` / `ai_insufficient_credits` / `ai_model_access` | Server/provider configuration problem. |
| 504 | `ai_timeout` / `ai_network_error` | Workflow, request or network timeout/failure. |

Provider exception text is never included in these responses. Real OpenAI connectivity requires a
valid key; automated tests use mocked clients and never call the paid API.

### Safe connectivity probe

Not an HTTP endpoint. From `backend/`:

```powershell
.\.venv\Scripts\python.exe -m app.cli.test_openai
```

It returns exit code 0 on a successful real structured request, 1 on a mapped failure and 2 when the
key is absent. It prints only status/model/attempts/duration. This performs a real request when a
key is present and is not part of automated verification.

---

## Settings — per-user OpenAI key (BYOK)

All four routes require authentication and operate on the **calling user's** key only. Their
`ApiKeyStatusResponse` never contains a plaintext secret.

| Method & path | Request | Response meaning |
| --- | --- | --- |
| `GET /api/v1/settings/api-keys` | — | Metadata for the caller's key: `success`, `provider: "openai"`, `configured`, `has_key`, `has_api_key`, `is_valid`, `status`, `key_hint`, `validated_at`, `last_used_at`. `status` is `not_configured`, `unvalidated`, `invalid` or `valid`. |
| `PUT /api/v1/settings/api-keys` | `{ "api_key": "sk-..." }` (8–512 chars, trimmed) | Validates with the provider first (`models.list()`), then encrypts and replaces the stored key. HTTP 400 `invalid_api_key` on rejection; no plaintext is returned or logged. |
| `POST /api/v1/settings/api-keys/validate` | — | Re-probes the stored key and refreshes its validity metadata. 404 `api_key_not_found` if absent; 400 `invalid_api_key` if rejected. |
| `DELETE /api/v1/settings/api-keys` | — | Removes the caller's key and returns a `not_configured` status. 404 `api_key_not_found` if absent. |

Purpose-built: the only plaintext egress is `byok.resolve_api_key()` inside an AI run. Provider
exceptions are reduced to booleans, `last_used_at` is refreshed on run resolution, and the
production config validator requires `BYOK_ENCRYPTION_KEY`.

---

## Knowledge base (governed documents)

Reads require **staff/HOD/admin**; uploads and mutations require **HOD/admin**. Documents are
stored in the database with extracted text and a checksum; no filesystem paths are returned.
Every upload creates a new, **unapproved** version; only approved + active rows are ever retrieved
by AI. All writes are audited.

### `GET /api/v1/knowledge`

| Query parameter | Type | Notes |
| --- | --- | --- |
| `skip` | int ≥ 0 | Pagination offset |
| `limit` | int 1–100 | Page size (default 20) |
| `search` | string ≤ 120 | Matches title, source key or content |
| `approved_only` | bool | Only approved rows |
| `active_only` | bool | Only active rows |
| `department_id` | int > 0 | Department filter (HODs restricted to their own) |

Returns `{ "success": true, "items": [KnowledgeDocumentResponse...], "total", "skip", "limit" }`.
HODs see global documents plus their own department; staff see all departments for reading.

### `POST /api/v1/knowledge`

HOD/admin only. `multipart/form-data` upload. Fields: `title` (1–255), `source_type` (`text`,
`txt`, `md`, `pdf`; default `text`), `source_key` (optional), `content` (inline text), `file`
(optional upload), `department_id` (optional, > 0). Returns HTTP 201 and the new document object
with `version`, `checksum`, `is_approved: false`, `is_active: true`. File bytes determine the
parsed type; mismatches are rejected, uploads over `MAX_UPLOAD_BYTES` (default 5 MiB) return HTTP
413 `upload_too_large`, and file extensions must be in `ALLOWED_UPLOAD_TYPES`.

### `GET /api/v1/knowledge/{document_id}`

Staff+. Returns metadata and extracted `content_text`. HODs cannot read another department's
document (403).

### `GET /api/v1/knowledge/{document_id}/versions`

Staff+. Returns `{ "success": true, "source_key", "items": [...], "total" }` for the document's
source key, newest first, with the same visibility rules.

### `PATCH /api/v1/knowledge/{document_id}`

HOD/admin only. Any subset of `title`, `content_text` (1–200000), `is_approved`, `is_active`,
`department_id`. Approval stamps `approved_by_id`/`approved_at`; approval and activation changes
are audited. HODs are limited to global or own-department documents.

### `DELETE /api/v1/knowledge/{document_id}`

HOD/admin only. **Soft deactivation**: sets `is_active: false` and returns the document object. No
knowledge row is ever hard-deleted, so the audit trail is preserved and AI retrieval stops seeing
the document.

---

## Analytics

### `GET /api/v1/analytics/overview`

Staff/HOD/admin only; no query parameters. Returns real SQL aggregates over the tickets the caller
may see — admin all, HOD their department, staff their assigned tickets; no sample or placeholder
data. `scope` describes the applied restriction. Response fields:

```json
{
  "success": true,
  "generated_at": "2026-11-21T21:10:00Z",
  "scope": "all",
  "role": "admin",
  "total_tickets": 42,
  "status_counts": { "new": 3, "assigned": 5, "in_progress": 4, "waiting_for_student": 2, "resolved": 20, "closed": 8 },
  "priority_counts": { "low": 10, "normal": 25, "high": 5, "urgent": 2 },
  "channel_counts": { "web": 38, "email": 2, "whatsapp": 2 },
  "escalated_count": 4,
  "resolved_count": 20,
  "backlog_count": 14,
  "avg_first_response_minutes": 34.5,
  "department_breakdown": [{ "department_id": 1, "department_name": "Registry", "total": 12 }],
  "ai_category_breakdown": [{ "category": "account_access", "total": 4 }],
  "monthly_volume": [{ "month": "2026-11", "total": 15 }]
}
```

`ai_category_breakdown` uses the latest AI analysis category per ticket. All counts are derived
from persisted rows; students receive HTTP 403.

---

## Announcements

Admin-managed, role/department-targeted broadcasts. Accepts the `audience_roles` field (or its
`audience_roles_json` alias) as a non-empty list of `student`, `staff`, `hod`, `admin`.

| Method & path | Authorization | Request / response meaning |
| --- | --- | --- |
| `GET /api/v1/announcements` | Any authenticated user | Returns only **active** broadcasts targeted at the caller's role and, when set, department. `{ "success": true, "items": [...], "total" }`. |
| `POST /api/v1/announcements` | Admin | Body `{ "title", "body", "audience_roles": ["student"], "department_id"?, "is_active"? }`; HTTP 201 with `AnnouncementResponse` (`id`, `published_at`, `created_by_id`, timestamps). |
| `PATCH /api/v1/announcements/{announcement_id}` | Admin | Any subset of the create fields; unknown roles are a Pydantic 422 `validation_error`. |
| `DELETE /api/v1/announcements/{announcement_id}` | Admin | **Soft deactivation** (`is_active: false`); the row stays for the audit trail and disappears from listings. |

---

## Leave (instructor absence windows)

Staff/HOD/admin only. Each window stores `start_at`, `end_at` (must be after `start_at`, else HTTP
400 `invalid_leave_window`), optional `reason`, required `auto_reply` text, `is_active`, and a
`user_id`. Staff may only manage their own windows; HODs only windows of users in their
department; admins all windows. Supplying `user_id` for another user as staff returns HTTP 403.
The `auto_reply` text is read by the reply worker while an active window covers the current time.

| Method & path | Response |
| --- | --- |
| `GET /api/v1/leave` | `{ "success": true, "items": [LeaveResponse...], "total" }` — own windows for staff, department windows for HOD, all for admin. |
| `POST /api/v1/leave` | HTTP 201 `LeaveMutationResponse` (`success`, `leave`, `message`). |
| `PATCH /api/v1/leave/{leave_id}` | `LeaveMutationResponse`; any subset of the create fields. |
| `DELETE /api/v1/leave/{leave_id}` | `LeaveMutationResponse`; soft deactivation, no hard delete. |

---

## Audit

### `GET /api/v1/audit`

Admin only. Returns real `AuditLog` rows (there are no synthetic authentication audits).

| Query parameter | Type | Notes |
| --- | --- | --- |
| `actor_id` | int > 0 | Filter by acting user |
| `action` | string ≤ 80 | Exact action, e.g. `ticket.created`, `ai.draft_approved` |
| `entity_type` | string ≤ 50 | e.g. `ticket`, `knowledge_document` |
| `entity_id` | string ≤ 50 | Entity identifier |
| `from` | datetime | Lower creation-time bound (Python field `date_from`) |
| `to` | datetime | Upper creation-time bound (Python field `date_to`) |
| `skip` | int ≥ 0 | Pagination offset (default 0) |
| `limit` | int 1–500 | Page size (default 50) |

```json
{
  "success": true,
  "items": [{ "id": 1, "actor_id": 2, "actor_email": "grace@university.edu", "actor_role": "staff", "action": "ticket.created", "entity_type": "ticket", "entity_id": "7", "details": {}, "is_override": false, "created_at": "2026-11-21T12:00:00Z" }],
  "total": 1,
  "skip": 0,
  "limit": 50
}
```

---

## Reports (PDF / Excel)

### `GET /api/v1/reports/tickets.pdf` and `GET /api/v1/reports/tickets.xlsx`

Staff/HOD/admin only. Both return a binary `StreamingResponse` — `application/pdf` or
`application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` — with
`Content-Disposition: attachment; filename="tickets-report.pdf"` (or `.xlsx`) and an
`X-Ticket-Count` header. Reports contain only role-scoped tickets (admin all, HOD department,
staff assigned) and a metadata header (`generated_at`, `scope`, `ticket_count`). Students receive
HTTP 403.

Both endpoints accept the same filters as the ticket list plus extras:

| Query parameter | Type | Notes |
| --- | --- | --- |
| `status`, `priority` | enum | Same values as the ticket list |
| `department_id`, `student_id`, `assigned_to` / `assignee_id` | int > 0 | `assigned_to` and `assignee_id` are aliases |
| `search` | string ≤ 120 | Matches subject/description |
| `from`, `to` | datetime | Creation-time bounds (query names `from` and `to`) |
| `channel` | enum | `web`, `email`, `whatsapp` |
| `is_escalated` / `escalated` | bool | Aliases |
| `skip` | int ≥ 0 | Offset |
| `limit` | int 1–10000 | Page size (default 1000) |

Browser downloads go through `GET /api/reports/{format}` on the BFF, which requires the session
cookie, restricts `format` to `pdf` or `xlsx`, and streams the binary upstream body unchanged with
`Cache-Control: no-store`.

---

## Notifications

Authenticated, scoped to the caller as `recipient_user_id`; a user cannot read or mark another
user's notification. Notification bodies are built only from public ticket events (created,
assigned, public reply, auto-reply, escalation, resolved, closed). **Internal notes and unapproved
AI drafts never produce notifications.**

| Method & path | Response |
| --- | --- |
| `GET /api/v1/notifications` | Query `skip` (int ≥ 0) and `limit` (int 1–100, default 20). Returns `{ "success": true, "items": [NotificationResponse...], "total", "skip", "limit" }`. Items include `channel`, `event_type`, `subject`, `body`, `status`, `attempts`, `last_error`, `provider_id`, `sent_at`, `read_at`, `is_internal`, timestamps. |
| `POST /api/v1/notifications/{notification_id}/read` | `{ "success": true, "notification": NotificationResponse }` with `read_at` set. A guessed/other user's id returns HTTP 404. |

Delivery itself is best-effort (email/WhatsApp depend on configuration); the notification row is
the durable record and outward-provider failures are recorded in `last_error`/`attempts`.

---

## Integrations (inbound intake + status)

### `GET /api/v1/integrations/status`

Public. Returns only non-sensitive configuration flags:

```json
{ "success": true, "smtp": true, "whatsapp": false, "google_oauth": false, "intake_webhook": true }
```

No secrets, addresses or tokens are returned. `google_oauth` is true only when OAuth is enabled
**and** a client id is configured; `intake_webhook` reflects whether `INTAKE_WEBHOOK_TOKEN` is set.

### `GET /api/v1/integrations/whatsapp/webhook`

Meta's GET verification handshake. Query parameters use Meta's alias names: `hub.mode`,
`hub.challenge`, `hub.verify_token`. The request must have `hub.mode=subscribe` and a constant-time
match against `WHATSAPP_VERIFY_TOKEN`; the configured challenge is echoed as `text/plain`. If the
verify token is unconfigured or mismatched, HTTP 401 with `code: "invalid_verify_token"` is returned.
This route fails closed and does not create tickets.

### `POST /api/v1/integrations/email/inbound`

Trusted mail-adapter webhook. Requires header `X-Intake-Token: <INTAKE_WEBHOOK_TOKEN>`. **Fail
closed:** if the server token is unconfigured, or the header is missing/mismatched, HTTP 401 with
`code: "invalid_intake_token"` (constant-time comparison via `hmac.compare_digest`).

```json
{
  "student_email": "ada@university.edu",
  "subject": "Cannot reset my password",
  "body": "I have tried the reset link twice and it expired.",
  "from_email": "ada@university.edu",
  "department_id": 1,
  "auto_route": true
}
```

`student_email` is the explicit caller-supplied mapping field used to resolve the account; the
untrusted `from_email` header is recorded for context but **never** used to identify or create a
user. An unknown student returns HTTP 404 `not_found`. A ticket is created with `channel: "email"`
and the response is `{ "success": true, "ticket": {...} }`.

### `POST /api/v1/integrations/whatsapp/inbound`

Same `X-Intake-Token` gate and fail-closed behavior. Body fields: `student_email`, `body` (10–10000),
optional `from_phone`, `student_phone`, `department_id`, `auto_route`. Phone numbers are contextual
only; the student is resolved from `student_email`. The subject is derived from the message body.
Creates a ticket with `channel: "whatsapp"` and returns `{ "success": true, "ticket": {...} }`.

Real inbound delivery depends on external adapters and credentials; this document does not claim
live end-to-end verification.

---

## Operations (SLA escalation)

### `POST /api/v1/tickets/escalation/run`

Admin only. Runs a deterministic, repeat-safe SLA sweep and returns:

```json
{ "success": true, "scanned": 3, "escalated": 2 }
```

The sweep selects non-terminal tickets older than `SLA_HOURS` (default 24) that are not already
escalated, marks each `is_escalated: true` with `escalated_at`, writes a status-history row and an
audit record (`ticket.escalated_automatically`, system actor), and notifies the student, assignee,
department HODs and admins. Because already-escalated rows are skipped, repeated calls do not
double-escalate. In `ENVIRONMENT=production` the same sweep also runs periodically in-process every
`ESCALATION_SWEEP_MINUTES`; it is never started in tests/development. This endpoint is deliberately
admin-only.

---

## Other error responses

Request: `GET /does-not-exist`

```json
{
  "success": false,
  "error": "Not Found",
  "detail": null,
  "code": null
}
```

Validation failures return HTTP 422 with `error: "Validation error"`, `code: "validation_error"`
and field-level problems in `detail` (JSON-safe). Unexpected failures return HTTP 500 with
`code: "internal_error"`; internal details are included only when `DEBUG=true`. Application errors
raised as `AppError` (including the 402/413/429 codes above) all use the same shared envelope.

---

## Configuration notes

- `ENVIRONMENT` gates unsafe tooling and dev-only fallback/worker behavior; `JWT_SECRET_KEY` and
  `BYOK_ENCRYPTION_KEY` are mandatory in production, and `ALLOW_GLOBAL_OPENAI_FALLBACK` cannot be
  enabled in production.
- `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` and `MIN_PASSWORD_LENGTH` tune authentication.
- Backend CORS origins come from `BACKEND_CORS_ORIGINS` (Vite dev server by default).
- Database settings come from `DATABASE_URL`, `TEST_DATABASE_URL`, `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`,
  `DB_POOL_TIMEOUT` and `DB_ECHO` in `backend/.env`.
- Vite frontend base URL comes from `VITE_API_BASE_URL` (see `frontend/.env.example`).
- Next.js frontend base URL comes from `NEXT_PUBLIC_API_BASE_URL`, optionally overridden by the
  server-only `API_BASE_URL` (see `frontend-next/.env.example`). No secrets belong in either value.
- AI settings in `backend/.env` are server-only: `OPENAI_API_KEY`, `OPENAI_MODEL`,
  `OPENAI_TIMEOUT_SECONDS`, `AI_MAX_INPUT_TOKENS`, `AI_MAX_OUTPUT_TOKENS`, `AI_LLM_ATTEMPTS`,
  `AI_GRAPH_TIMEOUT_SECONDS`, `AI_GRAPH_RECURSION_LIMIT`, `AI_MIN_CONFIDENCE`,
  `AI_KNOWLEDGE_FILE`, `BYOK_ENCRYPTION_KEY`, `ALLOW_GLOBAL_OPENAI_FALLBACK` and
  `AI_RATE_LIMIT_PER_MINUTE` (default 20).
- Google sign-in: `GOOGLE_OAUTH_ENABLED`, `GOOGLE_OAUTH_CLIENT_ID`.
- Inbound intake: `INTAKE_WEBHOOK_TOKEN`. Outbound email: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`,
  `SMTP_PASSWORD`, `MAIL_FROM`, `SMTP_USE_TLS`, `SMTP_USE_SSL`, `SMTP_TIMEOUT_SECONDS`,
  `SMTP_ATTEMPTS`, `EMAIL_NOTIFICATIONS_ENABLED`. Outbound WhatsApp: `WHATSAPP_ENABLED`,
  `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_VERIFY_TOKEN`,
  `WHATSAPP_API_VERSION`.
- SLA/operations: `SLA_HOURS`, `ESCALATION_SWEEP_MINUTES`. Uploads: `MAX_UPLOAD_BYTES`,
  `ALLOWED_UPLOAD_TYPES`.
- All `.env.example` files contain placeholders only; never commit real keys, tokens or passwords.
