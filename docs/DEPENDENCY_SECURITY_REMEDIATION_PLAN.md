# Smart Query System — Dependency Security Remediation Plan

**Audit Date:** 2026-11-23  
**Remediation Completed:** 2026-11-24 — Option B executed locally across all 3 stages (`vitest@4.1.12` + `vite@^7.3.8` + `@testing-library/dom@^10.4.2`, `zod@4.6.7`, and `next@16.4.6` + `eslint-config-next@16.4.6` with `--webpack` build script). Post-remediation `npm audit` and `npm audit --omit=dev` both report **0 vulnerabilities**. Historical pre-remediation audit notes remain below for traceability.  
**Machine-Readable Evidence:** [dependency_remediation_audit.json](file:///C:/Users/user/OneDrive/Desktop/SmartQuerySystem/docs/evidence/dependency_remediation_audit.json), [npm_audit_post_remediation.json](file:///C:/Users/user/OneDrive/Desktop/SmartQuerySystem/docs/evidence/npm_audit_post_remediation.json), [npm_audit_post_remediation_prod.json](file:///C:/Users/user/OneDrive/Desktop/SmartQuerySystem/docs/evidence/npm_audit_post_remediation_prod.json)

**Current release verdict:** **TECHNICAL RELEASE COMPLETE; FORMAL APPROVAL PENDING**; authoritative release status: `docs/evidence/phase5_live_verification_2026-11-24.json`.

---

## 1. Executive Summary

The 2026-11-23 read-only audit found **all 6 vulnerabilities** previously flagged in [npm_audit_summary.json](file:///C:/Users/user/OneDrive/Desktop/SmartQuerySystem/docs/evidence/npm_audit_summary.json) in [frontend-next/package.json](file:///C:/Users/user/OneDrive/Desktop/SmartQuerySystem/frontend-next/package.json). These findings are **historical**: all were remediated on 2026-11-24 as recorded at the top of this document. The inventory below is retained for traceability only:

- **Total vulnerabilities (`npm audit` in `frontend-next/`):** **6 vulnerabilities** (**2 Moderate, 2 High, 2 Critical**) spanning **10 unique GHSA advisories**.
- **Production-scope vulnerabilities (`npm audit --omit=dev` in `frontend-next/`):** **3 vulnerabilities** (**1 Moderate, 2 High, 0 Critical**): `next`, nested `postcss` (under `next`), and `zod`.
- **Development-only vulnerabilities:** **3 vulnerabilities** (**1 Moderate, 0 High, 2 Critical**): `vitest`, `@vitest/mocker`, and `tinypool`.
- **Legacy SPA (`frontend/`):** Live `npm audit` in [frontend/package.json](file:///C:/Users/user/OneDrive/Desktop/SmartQuerySystem/frontend/package.json) reports **0 vulnerabilities** (outdated packages `@vitejs/plugin-react` 4.7.0 → 6.3.0, `lucide-react` 0.500.0 → 1.78.0, and `vite` 6.4.6 → 8.3.8 have no audit findings).

**Key Finding on Safe vs. Major Upgrades:**
- A **non-breaking patch/minor run** (`npm audit fix` without `--force`) can **only** bump `vitest` `3.2.4 → 3.2.7`, resolving **1 of 10 advisories** (`GHSA-5xrq-8626-4rwp`) while leaving **all 6 packages flagged**.
- **Complete remediation (`0 vulnerabilities`) requires SemVer-major upgrades** across all three dependency trees:
  1. `vitest` **3.2.4 → 4.1.12** (resolves `vitest`, `@vitest/mocker`, and `tinypool`; importantly, **4.1.12** preserves Node 20 compatibility required by [frontend-next/Dockerfile](file:///C:/Users/user/OneDrive/Desktop/SmartQuerySystem/frontend-next/Dockerfile), whereas `vitest@5.1.1` requires Node `^22.12.0 || ^24.0.0 || >=26.0.0`).
  2. `zod` **3.25.76 → 4.6.7** (resolves `GHSA-mrhx-c7xc-m3w5`).
  3. `next` **15.5.29 → 16.4.6** + `eslint-config-next` **15.5.29 → 16.4.6** (updates bundled `postcss` from `8.4.31` past `<=8.5.22`, resolving `next` and nested `postcss`).

---

## 2. Verified 2026-11-23 Vulnerability Inventory (historical; remediated 2026-11-24)

All counts were re-verified directly against live lockfiles on Node `v22.23.2` / npm `10.9.0`:

| Package | Installed Version | Relationship | Scope | Severity | Affected Range | Advisories (GHSA / CWE / CVSS) | Patched Target | Upgrade Type |
|---|---|---|---|---|---|---|---|---|
| `next` | `15.5.29` | Direct (`dependencies`) | Production & Build | **Moderate** | `9.3.4-canary.0 - 16.3.0-preview.10` | Transitive via bundled `postcss@8.4.31` | `16.4.6` (+ `eslint-config-next@16.4.6`) | **Major (15 → 16)** |
| `postcss` *(nested)* | `8.4.31` *(at `node_modules/next/node_modules/postcss`)* | Transitive (`next@15.5.29`) | Production & Build | **High** | `<=8.5.22` | `GHSA-qx2v-qp2m-jg93` (Mod, CWE-79)<br>`GHSA-6g55-p6wh-862q` (High, CVSS 7.5, CWE-22/200)<br>`GHSA-fxqj-rqcc-2cmp` (Mod, CWE-22/200)<br>`GHSA-r28c-9q8g-f849` (High, CVSS 7.5, CWE-22) | `>=8.5.23` *(via `next@16.4.6`)* | **Major via `next`** |
| `zod` | `3.25.76` *(spec `^3.24.2`)* | Direct (`dependencies`) | Production (BFF) | **High** | `<4.6.6` | `GHSA-mrhx-c7xc-m3w5` (High, CVSS 7.5, CWE-770) | `4.6.7` | **Major (3 → 4)** |
| `vitest` | `3.2.4` *(spec `^3.2.4`)* | Direct (`devDependencies`) | Dev / Test only | **Critical** | `<=4.1.10` | `GHSA-5xrq-8626-4rwp` (Crit, CVSS 9.8, CWE-22/862)<br>`GHSA-82fw-gwwq-j7x9` (Mod, CVSS 5.9, CWE-22)<br>+ via `@vitest/mocker`, `tinypool` | `4.1.12` *(or `5.1.1` on Node ≥22.12)* | **Partial patch (`3.2.7`); Major (`4.1.12`) for full fix** |
| `@vitest/mocker` | `3.2.4` | Transitive (`vitest@3.2.4`) | Dev / Test only | **Moderate** | `<=4.1.11` | `GHSA-82fw-gwwq-j7x9` (Mod, CVSS 5.9, CWE-22)<br>`GHSA-qxg6-89mg-rqv8` (Mod, CVSS 4.7, CWE-94/116/306) | `>=4.1.12` *(via `vitest@4.1.12`)* | **Major via `vitest`** |
| `tinypool` | `1.1.1` | Transitive (`vitest@3.2.4`) | Dev / Test only | **Critical** | `<=2.1.1` | `GHSA-5gmw-xhrv-c9v3` (Crit, CWE-1321)<br>`GHSA-85c8-ppgw-ccpr` (Crit, CWE-94/1321) | `>=2.1.2` *(via `vitest@4.1.12`)* | **Major via `vitest`** |

> [!NOTE]
> `npm ls` confirms root `frontend-next/node_modules/postcss` is **`8.5.33`** (used by `@tailwindcss/postcss@4.3.5` and `vite@7.3.8`) and is **not vulnerable**. Only the private nested copy inside `node_modules/next/node_modules/postcss@8.4.31` is affected.

---

## 3. Production vs. Development Risk Assessment

### Production Runtime Scope (`next`, nested `postcss`, `zod`)
1. **`zod@3.25.76` (`GHSA-mrhx-c7xc-m3w5`, High / CVSS 7.5 — actual app risk: Low):**
   - Exploit vector is memory exhaustion when validating oversized constrained collections (arrays/sets/maps).
   - Codebase inspection confirms `zod` is imported in **only 3 unauthenticated/BFF auth endpoints**, and none define collection schemas:
     - [login/route.ts](file:///C:/Users/user/OneDrive/Desktop/SmartQuerySystem/frontend-next/src/app/api/auth/login/route.ts): two bounded strings (`max(255)`, `max(128)`).
     - [register/route.ts](file:///C:/Users/user/OneDrive/Desktop/SmartQuerySystem/frontend-next/src/app/api/auth/register/route.ts): four bounded strings (`max(128)`/`max(255)`/`email()`).
     - [google/route.ts](file:///C:/Users/user/OneDrive/Desktop/SmartQuerySystem/frontend-next/src/app/api/auth/google/route.ts): single bounded string (`min(10).max(20000)`).
2. **`postcss@8.4.31` via `next@15.5.29` (High / CVSS 7.5 — actual app risk: Low-to-Moderate):**
   - Processes static application stylesheets at build/compile time rather than user-supplied CSS at runtime. At the 2026-11-23 audit, `next` and `postcss` both failed `npm audit --omit=dev`, so CI/supply-chain scanners would have kept flagging production builds until `next` moved to `16.4.6+`; that upgrade is now completed and both audits report 0 vulnerabilities.

### Development & CI Build Scope (`vitest`, `@vitest/mocker`, `tinypool`)
1. **`vitest@3.2.4` / `@vitest/mocker@3.2.4` / `tinypool@1.1.1` (Critical — actual deployed runtime risk: None; local/CI dev risk: Moderate-to-High if exposed):**
   - [frontend-next/Dockerfile](file:///C:/Users/user/OneDrive/Desktop/SmartQuerySystem/frontend-next/Dockerfile#L42-L48) builds the final `runner` stage with `RUN npm ci --omit=dev --no-audit --no-fund`, copying only `node_modules/typescript` from `deps`. Therefore, none of the 3 dev-only vulnerable packages ship in the production container image.
   - During local/CI execution, `GHSA-5xrq-8626-4rwp` allows arbitrary file access/execution when the Vitest UI server is listening, and `tinypool` prototype pollution requires untrusted test worker options. Never expose Vitest dev/UI servers beyond localhost.

---

## 4. Remediation Options

### Option A — Minimum-Risk Non-Breaking Patch/Minor Updates Only

- **Action:** Update only `vitest` from `3.2.4` to `3.2.7` (`wanted` compatible semver patch).
- **Security Outcome:**
  - Patches `GHSA-5xrq-8626-4rwp` (Critical on `vitest`).
  - **Leaves 6/6 packages and 9/10 GHSAs unresolved:** `GHSA-82fw-gwwq-j7x9` on `vitest` (`<4.1.11`), both advisories on `@vitest/mocker` (`<4.1.12`), both critical advisories on `tinypool` (`<2.1.2`), `zod` (`<4.6.6`), and `next` + nested `postcss`.
- **Verdict (historical assessment):** **Insufficient** as a final state at audit time (it would have failed both `npm audit` and `npm audit --omit=dev`), useful only as a stopgap before Option B. Option B was completed on 2026-11-24; both audits now report 0 vulnerabilities.

---

### Option B — Full Remediation via Major Upgrades (Recommended)

Upgrade all affected packages in a controlled, phased order across three isolated PRs/commits:
1. **`vitest` `^3.2.4` → `^4.1.12`** (dev/test isolation)
2. **`zod` `^3.24.2` → `^4.6.7`** (BFF schema migration)
3. **`next` `15.5.29` → `16.4.6` + `eslint-config-next` `15.5.29` → `16.4.6`** (framework & lint alignment)

#### Breaking-Change & Affected-File Analysis

1. **Step 1 — Vitest `3.2.4 → 4.1.12` (Prefer `4.1.12` over `5.1.1`):**
   - **Why `4.1.12` over `5.1.1`:** [frontend-next/Dockerfile](file:///C:/Users/user/OneDrive/Desktop/SmartQuerySystem/frontend-next/Dockerfile#L9) uses `FROM node:20-alpine` in its `deps` stage. `vitest@5.1.1` requires `node: '^22.12.0 || ^24.0.0 || >=26.0.0'`, which would break the Docker `deps` stage unless `Dockerfile` base images are bumped to `node:22-alpine`. `vitest@4.1.12` supports `node: '^20.0.0 || ^22.0.0 || >=24.0.0'` and `vite: '^6.0.0 || ^7.0.0 || ^8.0.0'` (installed Vite is `7.3.8`), while resolving `vitest`, `@vitest/mocker`, and `tinypool` completely.
   - **Affected files:**
     - [frontend-next/package.json](file:///C:/Users/user/OneDrive/Desktop/SmartQuerySystem/frontend-next/package.json)
     - [frontend-next/vitest.config.ts](file:///C:/Users/user/OneDrive/Desktop/SmartQuerySystem/frontend-next/vitest.config.ts) (`environment: 'jsdom'`, `setupFiles`, `include`, `css: false`)
     - [frontend-next/src/test/setup.ts](file:///C:/Users/user/OneDrive/Desktop/SmartQuerySystem/frontend-next/src/test/setup.ts) (`afterEach(cleanup)`)
     - [frontend-next/src/hooks/useTicketStatusPolling.test.tsx](file:///C:/Users/user/OneDrive/Desktop/SmartQuerySystem/frontend-next/src/hooks/useTicketStatusPolling.test.tsx) (`vi.mock`, `vi.mocked`, `vi.fn` — 3 unit tests)
   - **Risks:** Vitest 4 pool/mocking defaults (`vi.mock` behavior and `@vitest/mocker` module resolution with `jsdom` 26.1.0). Surface area is minimal (1 test file, 3 tests).

2. **Step 2 — Zod `3.25.76 → 4.6.7`:**
   - **Affected files (complete list across repository):**
     - [login/route.ts](file:///C:/Users/user/OneDrive/Desktop/SmartQuerySystem/frontend-next/src/app/api/auth/login/route.ts): uses `z.object`, `z.string().trim().min(1).max(255)`, `safeParse`, and `parsed.error.flatten()`.
     - [register/route.ts](file:///C:/Users/user/OneDrive/Desktop/SmartQuerySystem/frontend-next/src/app/api/auth/register/route.ts): uses `z.string().trim().email().max(255)` and `parsed.error.flatten()`.
     - [google/route.ts](file:///C:/Users/user/OneDrive/Desktop/SmartQuerySystem/frontend-next/src/app/api/auth/google/route.ts): uses `z.object({ credential: z.string().min(10).max(20000) })` and `safeParse`.
   - **Required Zod v4 Code Adjustments:**
     - Replace `z.string().trim().email().max(255)` in `register/route.ts` with Zod v4's top-level `z.email()` chained with `.trim().max(255)` (or `.pipe(z.email())`), since `.email()` on `ZodString` is deprecated/changed in Zod v4.
     - Replace `parsed.error.flatten()` in `login/route.ts` and `register/route.ts` with `z.flattenError(parsed.error)` and verify HTTP `400` validation response shape `{ success: false, error: '...', detail: { fieldErrors, formErrors }, code: 'validation_error' }` remains byte-compatible with frontend form error handling.

3. **Step 3 — Next.js `15.5.29 → 16.4.6` & `eslint-config-next` `15.5.29 → 16.4.6`:**
   - **Codebase readiness checks already favorable:**
     - `cookies()` in [cookies.ts](file:///C:/Users/user/OneDrive/Desktop/SmartQuerySystem/frontend-next/src/lib/auth/cookies.ts) is already async (`await cookies()`).
     - Dynamic route `params` in [tickets/[ticketId]/page.tsx](file:///C:/Users/user/OneDrive/Desktop/SmartQuerySystem/frontend-next/src/app/(protected)/tickets/[ticketId]/page.tsx), [backend/[...path]/route.ts](file:///C:/Users/user/OneDrive/Desktop/SmartQuerySystem/frontend-next/src/app/api/backend/[...path]/route.ts), and [reports/[format]/route.ts](file:///C:/Users/user/OneDrive/Desktop/SmartQuerySystem/frontend-next/src/app/api/reports/[format]/route.ts) already type `params` as `Promise<...>` and `await` it.
     - [next.config.ts](file:///C:/Users/user/OneDrive/Desktop/SmartQuerySystem/frontend-next/next.config.ts) contains only `{ reactStrictMode: true, poweredByHeader: false }` (no legacy `images.domains` or deprecated `experimental.*` flags).
     - `@mui/material-nextjs@7.3.10` already declares `"next": "^13.0.0 || ^14.0.0 || ^15.0.0 || ^16.0.0"` in `peerDependencies` and ships `v16-appRouter/`.
     - `@playwright/test@^1.65.1` already satisfies `next@16.4.6` peer dependency `^1.51.1`.
     - Node `>=20.9.0` engine requirement is satisfied by `Dockerfile` (`node:20-alpine` — verify exact `20.x` patch in Docker image pull is `>=20.9.0`, or pin `node:20.19-alpine` / `node:22-alpine`).
   - **Expected Breaking Areas to Update:**
     - [eslint.config.mjs](file:///C:/Users/user/OneDrive/Desktop/SmartQuerySystem/frontend-next/eslint.config.mjs): currently wraps legacy configs with `FlatCompat` (`compat.extends('next/core-web-vitals', 'next/typescript')`). `eslint-config-next@16.x` exports native ESLint 9 flat config arrays directly, which commonly throws circular/type errors under `FlatCompat` — migrate `eslint.config.mjs` to direct flat-config imports (`next/core-web-vitals` & `next/typescript` flat presets).
     - [src/app/layout.tsx](file:///C:/Users/user/OneDrive/Desktop/SmartQuerySystem/frontend-next/src/app/layout.tsx#L2): update import `@mui/material-nextjs/v15-appRouter` → `@mui/material-nextjs/v16-appRouter`.
     - Verify Tailwind CSS v4 (`@tailwindcss/postcss@4.3.5`), MUI 7 (`enableCssLayer: true`), `next build` output across all app pages and API routes, and `next start` healthcheck in [playwright.config.ts](file:///C:/Users/user/OneDrive/Desktop/SmartQuerySystem/frontend-next/playwright.config.ts) and [Dockerfile](file:///C:/Users/user/OneDrive/Desktop/SmartQuerySystem/frontend-next/Dockerfile).

---

### Option C — Temporary Mitigations (Until Option B Executes)

If deployment or audit clearance must pause before major upgrades:
1. **Maintain dev-dependency exclusion in production images:** Keep `npm ci --omit=dev` in [frontend-next/Dockerfile](file:///C:/Users/user/OneDrive/Desktop/SmartQuerySystem/frontend-next/Dockerfile#L43) so `vitest`, `@vitest/mocker`, and `tinypool` never exist in runtime containers.
2. **Restrict Vitest execution context:** Run Vitest only in trusted local/CI contexts on static workspace files; do not start Vitest UI (`--ui`) or expose any dev test port outside `127.0.0.1`.
3. **Preserve strict Zod BFF bounds:** Keep explicit `.max(...)` string bounds (`128`/`255`/`20000`) on `login`, `register`, and `google` routes and reject oversized JSON request payloads upstream/reverse-proxy level (e.g., `<= 64 KB` on auth routes) so `GHSA-mrhx-c7xc-m3w5` has no collection-allocation vector.
4. **Build-time CSS isolation:** Ensure `next build` processes only version-controlled CSS in `src/app/globals.css`, mitigating `postcss@8.4.31` advisories until `next@16.4.6` lands.

---

## 5. Recommended Strategy & Ordered Execution Sequence

**Recommendation:** Adopt **Option B** with `vitest@4.1.12` (not `5.1.1` unless `Dockerfile` is concurrently upgraded from `node:20-alpine` to `node:22-alpine`), executed in this strict sequence so each change can be isolated and rolled back independently:

1. **Phase 1 (Lowest Risk, Dev-Only):** Upgrade `vitest` to `^4.1.12` (update lockfile, verify `npm ls` confirms `tinypool >= 2.1.2` and `@vitest/mocker >= 4.1.12`). Run `npm test` (Vitest) and `npm run lint`.
2. **Phase 2 (Focused Prod BFF Change):** Upgrade `zod` to `^4.6.7`. Update `z.email()` and `z.flattenError()` in `login/route.ts` and `register/route.ts`, and verify `google/route.ts`. Run `typecheck`, auth negative-validation tests, and Playwright E2E `auth.spec.ts`.
3. **Phase 3 (Framework & Lint Migration):** Upgrade `next` and `eslint-config-next` to `16.4.6`. Update [eslint.config.mjs](file:///C:/Users/user/OneDrive/Desktop/SmartQuerySystem/frontend-next/eslint.config.mjs) for native ESLint 9 flat config and [src/app/layout.tsx](file:///C:/Users/user/OneDrive/Desktop/SmartQuerySystem/frontend-next/src/app/layout.tsx) to `@mui/material-nextjs/v16-appRouter`. Verify `npm audit` and `npm audit --omit=dev` both return `0 vulnerabilities`.
4. **Phase 4 (Full Verification & Container Check):** Execute the complete Regression & Compatibility Plan below, including Docker image build verification if `Dockerfile` is modified or deployed.

---

## 6. Complete Regression & Compatibility Test Plan

After each phase (and cumulatively after Phase 3), execute and record evidence for:

1. **Audit & Toolchain Integrity (`frontend-next/`):**
   - `npm audit` → `found 0 vulnerabilities`
   - `npm audit --omit=dev` → `found 0 vulnerabilities`
   - `npm run lint` → 0 errors / warnings
   - `npx tsc --noEmit` → clean typecheck
   - `npm test` (Vitest) → all unit tests pass (`useTicketStatusPolling.test.tsx`)
   - `npm run build` → clean production build across all Next.js app and API routes (`next build`)
2. **Backend Regression (`backend/`):**
   - `.venv\Scripts\python.exe -m pytest -q` → verify full backend suite (`229 passed`) remains intact alongside updated BFF contracts.
3. **End-to-End & Accessibility (`frontend-next/`):**
   - `npx playwright test` (Playwright + `@axe-core/playwright`) → verify full 12-test suite passes against compiled `next start`.
4. **Functional Smoke & Security Flows (Local Demo / BFF):**
   - **Auth & RBAC:** Student/Staff/HOD/Admin login (`/api/auth/login`), registration validation error shapes (`/api/auth/register` malformed email & short password), Google SSO handler schema (`/api/auth/google`), `HttpOnly` cookie session + CSRF header enforcement on BFF mutations (`/api/backend/[...path]`).
   - **BYOK Isolation:** User personal OpenAI key `POST`/`GET`/`DELETE` flow in Settings without exposing keys.
   - **Tickets, Routing & Escalation:** Ticket creation, department routing, assignment, escalation/de-escalation audit history (`TicketHistory`), and notification delivery.
   - **Notifications & Attachments:** Polling/real-time notification list + mark-read, attachment upload multipart forwarding through `/api/backend/[...path]` and report streaming (`/api/reports/pdf`, `/api/reports/xlsx`).
   - **Container Build Verification:** `docker build -t smartquery-frontend ./frontend-next` verifying `node:20-alpine` (≥20.9.0) or bumped Node base completes `npm ci`, `npm run build`, `npm ci --omit=dev`, and `/api/health` check.

---

## 7. Remaining Risks & Limitations

- **Historical unpatched state (2026-11-23):** At audit time all 6 vulnerabilities in `frontend-next` were active because that audit strictly preserved `package.json`, `package-lock.json`, and all source files. They were remediated on 2026-11-24; no finding remains active.
- **Registry reachability in offline/sandboxed environments:** `npm audit` / `npm view` network calls fail with `ENOTFOUND registry.npmjs.org` when offline or sandboxed without registry access; remediation installation must run in an environment with npm registry connectivity (or mirrored internal registry).
- **Docker Node 20 base pin:** Moving `vitest` to `5.x` in the future requires upgrading `node:20-alpine` in [frontend-next/Dockerfile](file:///C:/Users/user/OneDrive/Desktop/SmartQuerySystem/frontend-next/Dockerfile) to Node `>=22.12.0` (`node:22-alpine`). Sticking with `vitest@4.1.12` avoids a forced Node base bump while eliminating every Vitest-tree CVE.
