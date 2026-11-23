# Final Local Demo & Verification Guide

Use this guide to demonstrate all verified capabilities of the **Smart Query Routing & Email Automation System** locally with zero external costs or production changes.

---

## 1. Prerequisites
- **Python 3.12+** with existing virtual environment in `backend\.venv\Scripts\python.exe` (verified on Python 3.14.7)
- **Node.js 20.9+** and npm (`v22.23.2` / `npm 10.9.0` verified locally)
- **Docker Desktop** (optional for PostgreSQL / full-stack containers; offline SQLite demo script needs no Docker)

---

## 2. Option 1 — Quick Offline Local Demo (`start_local_demo.ps1`)

From the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start_local_demo.ps1
```

This starts an isolated local demo backend (SQLite + deterministic ticket-grounded mock AI) and the Next.js 16 BFF frontend (`http://127.0.0.1:3000` / backend `http://127.0.0.1:8010`) with synthetic seeded users documented in `docs/DEMO_TEST_DATA_GUIDE.md`. Never use these demo accounts in production.

---

## 3. Option 2 — Full Automated Verification Walkthrough

### Backend Full Suite (229 tests)
```powershell
$env:DEBUG='false'
cd backend
.\.venv\Scripts\python.exe -m compileall -q app tests evaluations
.\.venv\Scripts\python.exe -m alembic heads
.\.venv\Scripts\python.exe -m pytest -q
```
Expected: `feedf21773e1 (head)` and **229 passed**. *(Note: run outside restricted sandboxes that block `127.0.0.1` loopback `socketpair()` calls.)*

### Frontend Static, Unit, Build, Audit & Playwright/Axe Suite
```powershell
cd frontend-next
npm audit
npm audit --omit=dev
npm run typecheck
npm run lint
npm run test
npm run build
$env:DEBUG='false'
npm run test:e2e
```
Expected:
- `npm audit` / `npm audit --omit=dev`: **0 vulnerabilities**
- `npm run test` (Vitest 4.1.12): **3 passed**
- `npm run build` (`next build --webpack` on Next.js 16.4.6): **0 errors**
- `npm run test:e2e`: **12 passed** (Chromium + Axe accessibility scans across login, student workspace, ticket detail, escalation/de-escalation history, and staff notifications)

### Disposable PostgreSQL Migration & Backup/Restore Rehearsal
```powershell
$env:DEBUG='false'
.\scripts\backup_restore_rehearsal.ps1
```
Expected: `Backup/restore rehearsal: PASS` (uses disposable `postgres:16-alpine` on `127.0.0.1:55432` and cleans up automatically).

---

## 4. Recommended Live Demo Flow (4 Roles)
1. **Student (`/login` -> `/student`):** Sign in, submit a query (`Registry` / `Scholarships`), observe `TKT-...` reference, and verify conditional live status polling on `/tickets/[ticketId]`.
2. **Staff (`/staff` -> `/tickets/[ticketId]`):** View assigned ticket, test personal OpenAI BYOK status / fail-closed `402` guard (or demo mock AI consistency & KB citations), post an internal note (verify student view hides it), and publish an approved response.
3. **HOD (`/hod` -> `/leave` -> `/knowledge`):** Toggle instructor leave window, upload/approve knowledge document, escalate and de-escalate a ticket, and inspect the **Escalations** section in Recorded History + deduplicated Notification Centre delivery.
4. **Admin (`/admin` -> `/analytics` -> `/audit`):** View system-wide analytics charts, export PDF/XLSX reports (`/api/reports/pdf`, `/api/reports/xlsx`), broadcast an announcement, and review append-only audit logs (including authentication outcomes).
