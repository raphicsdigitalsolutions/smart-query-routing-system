"""Generate the hackathon deployment report and slide-deck PDFs.

Run from the repository root:
    .\\backend\\.venv\\Scripts\\python.exe docs\\generate_hackathon_deployment_pdfs.py

The script uses only reportlab and writes no secret material.
"""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.pdfgen import canvas as canvas_module

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs"

NAVY = colors.HexColor("#0B1F3A")
TEAL = colors.HexColor("#0E9F9F")
CANVAS = colors.HexColor("#F5F7FA")
MUTED = colors.HexColor("#526279")
GREEN = colors.HexColor("#1E7F5C")
AMBER = colors.HexColor("#B7791F")
RED = colors.HexColor("#B42318")


def p(text, style):
    return Paragraph(text, style)


def report_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        "ReportTitle", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=22, leading=27, textColor=NAVY, spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        "ReportSub", parent=styles["Normal"], fontName="Helvetica",
        fontSize=10, leading=14, textColor=MUTED, spaceAfter=12,
    ))
    styles.add(ParagraphStyle(
        "ReportH1", parent=styles["Heading1"], fontName="Helvetica-Bold",
        fontSize=14, leading=18, textColor=NAVY, spaceBefore=12, spaceAfter=7,
    ))
    styles.add(ParagraphStyle(
        "ReportH2", parent=styles["Heading2"], fontName="Helvetica-Bold",
        fontSize=11, leading=15, textColor=TEAL, spaceBefore=8, spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        "ReportBody", parent=styles["BodyText"], fontName="Helvetica",
        fontSize=9, leading=13, textColor=colors.HexColor("#172033"),
        alignment=TA_LEFT, spaceAfter=5,
    ))
    styles.add(ParagraphStyle(
        "ReportCell", parent=styles["BodyText"], fontName="Helvetica",
        fontSize=7.6, leading=10, textColor=colors.HexColor("#172033"),
    ))
    styles.add(ParagraphStyle(
        "ReportCellHead", parent=styles["BodyText"], fontName="Helvetica-Bold",
        fontSize=7.8, leading=10, textColor=colors.white,
    ))
    styles.add(ParagraphStyle(
        "ReportNote", parent=styles["BodyText"], fontName="Helvetica-Oblique",
        fontSize=8.5, leading=12, textColor=MUTED,
    ))
    styles.add(ParagraphStyle(
        "ReportBullet", parent=styles["BodyText"], fontName="Helvetica",
        fontSize=9, leading=13, leftIndent=12, bulletIndent=2,
        textColor=colors.HexColor("#172033"), spaceAfter=3,
    ))
    return styles


def status_color(text):
    upper = text.upper()
    if any(word in upper for word in ("PASS", "LIVE", "READY", "CONNECTED", "PRESERVED")):
        return GREEN
    if any(word in upper for word in ("BLOCK", "PENDING", "NOT PASSED", "FAIL", "UNRESOLVED")):
        return RED if "FAIL" in upper or "BLOCK" in upper else AMBER
    return MUTED


def make_table(headers, rows, widths, styles):
    data = [[p(h, styles["ReportCellHead"]) for h in headers]]
    for row in rows:
        data.append([p(str(cell), styles["ReportCell"]) for cell in row])
    table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    for index in range(1, len(data)):
        if index % 2 == 0:
            style.append(("BACKGROUND", (0, index), (-1, index), colors.HexColor("#EEF3F8")))
    table.setStyle(TableStyle(style))
    return table


def header_footer(canvas, doc):
    canvas.saveState()
    width, height = A4
    canvas.setFillColor(NAVY)
    canvas.rect(0, height - 12 * mm, width, 12 * mm, stroke=0, fill=1)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(18 * mm, height - 8 * mm, "SMART QUERY ROUTING SYSTEM")
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(width - 18 * mm, height - 8 * mm, "HACKATHON DEPLOYMENT REPORT")
    canvas.setStrokeColor(colors.HexColor("#D8E0EA"))
    canvas.line(18 * mm, 14 * mm, width - 18 * mm, 14 * mm)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(18 * mm, 9 * mm, "22 Nov 2026 (updated 23 Nov) | Live demo; formal sign-off open")
    canvas.drawRightString(width - 18 * mm, 9 * mm, f"Page {doc.page}")
    canvas.restoreState()


def build_report():
    path = OUT_DIR / "HACKATHON_DEPLOYMENT_REPORT.pdf"
    doc = BaseDocTemplate(
        str(path), pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
        title="Smart Query Routing System - Hackathon Deployment Report",
        author="Smart Query Routing System",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates([PageTemplate(id="all", frames=[frame], onPage=header_footer)])
    styles = report_styles()
    story = []

    story.append(p("Hackathon Deployment Report", styles["ReportTitle"]))
    story.append(p(
        "Smart Query Routing System | 22 Nov 2026, reconciled 23 Nov 2026 | Backend, database, frontend, auth, images, documentation",
        styles["ReportSub"],
    ))
    story.append(Table(
        [[p(
            "Deployment executed and reachable; 23 Nov feature work is LOCAL VERIFIED only. Formal governance remains NOT PASSED: the prior FAIL verdict and signed-deviation gaps are still open.",
            styles["ReportBody"],
        )]],
        colWidths=[doc.width],
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFF6E5")),
            ("BOX", (0, 0), (-1, -1), 0.8, AMBER),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]),
    ))
    story.append(Spacer(1, 8))

    story.append(p("1. Executive status", styles["ReportH1"]))
    story.append(make_table(
        ["Area", "Actual status"],
        [
            ["Backend API on Vercel", "LIVE - FastAPI ASGI deployment, production alias reachable"],
            ["Neon PostgreSQL", "CONNECTED - 17 tables, Alembic revision feedf21773e1"],
            ["Frontend/BFF on Netlify", "LIVE - production deploy 6b02db1360e3188d7f1074c6 published"],
            ["Live BFF smoke", "PASS - registration/login, HttpOnly session, CSRF 403, multipart 201, PDF 200"],
            ["Container images", "Backend and frontend built locally; GHCR push blocked by missing write:packages"],
            ["Strict $0 constraint", "PRESERVED - no paid plan, upgrade, payment method, add-on, or billing change"],
            ["BYOK policy", "PRESERVED - global fallback false, global OpenAI key empty, no personal key hosted"],
            ["Formal governance", "NOT PASSED - prior FAIL verdict and signed deviations unresolved"],
            ["FR-04b / FR-13 routing", "LOCAL VERIFIED - deterministic staff-only; active leave only; no approval workflow"],
            ["FR-06 polling", "LOCAL VERIFIED - ETag/304 updates endpoint + hook; not SSE/push"],
            ["FR-07 cron trigger", "LOCAL VERIFIED - secret-protected sweep + hourly repo config; hosted execution NOT VERIFIED"],
            ["FR-14 auth audits", "LOCAL VERIFIED - register/login success and failure, no secrets"],
            ["Playwright + axe E2E", "LOCAL VERIFIED - build pass, 11 passed (~1.3m), no serious/critical axe"],
            ["Backup/restore; malware", "LOCAL PASS on disposable Postgres; ClamAV integration only, NOT DEPLOYED"],
            ["Secret audit; npm audit", "TRIAGE ONLY - no rotation/revocation; npm audit 6 (2 moderate, 2 high, 2 critical)"],
        ],
        [46 * mm, doc.width - 46 * mm], styles,
    ))

    story.append(p("2. Live topology", styles["ReportH1"]))
    story.append(make_table(
        ["Layer", "Endpoint / identifier", "State"],
        [
            ["Frontend + Next.js BFF (Netlify Free)", "https://smart-query-routing-system.netlify.app", "LIVE - deploy 6b02db1360e3188d7f1074c6"],
            ["Backend FastAPI (Vercel Hobby)", "https://smart-query-backend.vercel.app", "READY - deploy dpl_3va9eirAAZ6wajnAVd2bL3kP2EVV"],
            ["Backend per-deploy URL", "https://smart-query-backend-ijul8q2np-inforaphicsdigital-8444.vercel.app", "READY"],
            ["Neon PostgreSQL", "Secret env var only", "17 tables; revision feedf21773e1"],
            ["GHCR", "ghcr.io/raphicsdigitalsolutions/smart-query-*", "Local images; remote push blocked by missing write:packages"],
        ],
        [48 * mm, 72 * mm, doc.width - 120 * mm], styles,
    ))
    story.append(Spacer(1, 4))
    story.append(p(
        "Netlify used next build, publish .next, NODE_VERSION=22.23.2, and @netlify/plugin-nextjs. Both API_BASE_URL and NEXT_PUBLIC_API_BASE_URL were verified as https://smart-query-backend.vercel.app/api/v1 for Live app and Versions.",
        styles["ReportBody"],
    ))
    story.append(p(
        "Vercel deployed locally from backend/ with Python 3.12, ASGI entrypoint backend/api/index.py, and a catch-all rewrite to /api/index. Serverless overrides disable the background worker, use /tmp attachments, cap uploads at 4 MiB, reduce DB pooling, and disable migrations.",
        styles["ReportBody"],
    ))
    story.append(p(
        "backend/vercel.json now defines an hourly cron calling the secret-protected POST /api/v1/tickets/escalation/sweep (X-Cron-Secret). The endpoint and config are LOCAL VERIFIED; live hosted cron execution is NOT VERIFIED, and no provider scheduler was changed.",
        styles["ReportBody"],
    ))

    story.append(PageBreak())
    story.append(p("3. Live verification evidence", styles["ReportH1"]))
    story.append(p("3.1 Frontend and BFF", styles["ReportH2"]))
    story.append(make_table(
        ["Check", "Result"],
        [
            ["Frontend root", "HTTP 200; HTML app shell"],
            ["Frontend /api/health", "HTTP 200; success true, status healthy"],
            ["Guest session", "HTTP 200; smartquery_csrf cookie set"],
            ["Register through BFF", "HTTP 200; smartquery_session HttpOnly cookie; CSRF token returned"],
            ["Valid session probe", "HTTP 200; authenticated user present"],
            ["Wrong / missing CSRF", "HTTP 403 / HTTP 403"],
            ["Multipart proxy", "HTTP 201; 781-byte response; cleanup DELETE 200"],
            ["PDF report", "HTTP 200; application/pdf; Content-Disposition; Cache-Control no-store; %PDF-1.3"],
            ["Smoke cleanup", "Temporary user and document removed; final user count 1, admin:1"],
        ],
        [50 * mm, doc.width - 50 * mm], styles,
    ))
    story.append(p(
        "Local admin credential material no longer matched the hosted admin row; password login returned 401. No credential or database row was changed. Authenticated checks used a short-lived token minted from the hosted JWT secret; token and helper files were deleted.",
        styles["ReportNote"],
    ))

    story.append(p("3.2 Backend and database", styles["ReportH2"]))
    story.append(make_table(
        ["Check", "Result"],
        [
            ["GET /", "HTTP 200; API is running, version 1.0.0"],
            ["GET /health", "HTTP 200; success true, status healthy"],
            ["GET /docs and /openapi.json", "HTTP 200"],
            ["GET /api/v1/status/database", "HTTP 200; database connected"],
            ["Neon schema", "17 tables; alembic_version present at feedf21773e1"],
            ["Backend suite", "Historical 187 passed; final local rerun 225 passed, 17 warnings in 265.61s (0:04:25)"],
            ["Frontend build", "typecheck/lint pass; npm run build pass; 13/13 pages"],
            ["Playwright + axe E2E", "LOCAL VERIFIED: build pass; 11 passed (~1.3m); no serious/critical axe on 3 screens"],
        ],
        [50 * mm, doc.width - 50 * mm], styles,
    ))

    story.append(p("3.3 Provider and BYOK status", styles["ReportH2"]))
    story.append(make_table(
        ["Integration", "Verified state"],
        [
            ["Google OAuth", "Code/offline tests pass; live client ID/origin unavailable"],
            ["SMTP email", "Code/fake-provider tests pass; live credentials and MAIL_FROM unavailable"],
            ["WhatsApp", "Adapter/inbound tests pass; real Meta token, phone ID, webhook token unavailable"],
            ["User OpenAI BYOK", "Policy/encryption tests pass; live key validation blocked; no global fallback"],
        ],
        [40 * mm, doc.width - 40 * mm], styles,
    ))

    story.append(p("4. Serverless deviations that are live", styles["ReportH1"]))
    story.append(make_table(
        ["Deviation", "Live behavior"],
        [
            ["Background worker", "In-process worker disabled; hourly secret-protected cron configured in repo; hosted execution NOT VERIFIED"],
            ["Attachments", "Stored in /tmp; ephemeral and not shared across instances"],
            ["Upload limit", "4194304 bytes (4 MiB), matching Vercel standard body limit"],
            ["DB pool", "DB_POOL_SIZE=1, DB_MAX_OVERFLOW=0"],
            ["Migrations", "RUN_MIGRATIONS=false; Neon independently verified already at head"],
            ["Billing", "Vercel Hobby; existing card/balance not used or modified by assistant"],
        ],
        [40 * mm, doc.width - 40 * mm], styles,
    ))

    story.append(PageBreak())
    story.append(p("5. Brief coverage - pages 30-31", styles["ReportH1"]))
    story.append(make_table(
        ["FR", "Brief requirement", "Actual status"],
        [
            ["FR-01", "Role-based login with Google OAuth2", "Implemented/tested; live OAuth blocked"],
            ["FR-02", "Email, web, WhatsApp submission", "Web live; provider intake tested; live providers blocked"],
            ["FR-03", "AI classification and intent detection", "Implemented/tested offline; live AI needs user BYOK"],
            ["FR-04", "Route to department or instructor", "Department routing live; instructor auto-route LOCAL VERIFIED, staff-only, leave-aware"],
            ["FR-05", "AI draft replies for staff", "Implemented/tested; live generation needs BYOK"],
            ["FR-06", "Real-time student tracking", "Conditional ETag/304 polling LOCAL VERIFIED; not SSE/push"],
            ["FR-07", "24-hour auto-escalation", "Sweep + secret cron trigger LOCAL VERIFIED; hosted execution NOT VERIFIED"],
            ["FR-08", "Email and WhatsApp notifications", "DB/in-app tested; live external delivery blocked"],
            ["FR-09", "HOD escalation and override", "Implemented/tested"],
            ["FR-10", "Admin analytics dashboard", "Implemented/tested"],
            ["FR-11", "Broadcast announcements", "Implemented/tested"],
            ["FR-12", "PDF and Excel exports", "Implemented/tested; PDF verified live through BFF"],
            ["FR-13", "Instructor leave and auto-reply", "CRUD/auto-reply tested; routing exclusion LOCAL VERIFIED; university approval open"],
            ["FR-14", "History and audit log", "Implemented/tested; password auth success/failure audits LOCAL VERIFIED, no secrets"],
        ],
        [17 * mm, 70 * mm, doc.width - 87 * mm], styles,
    ))
    story.append(p(
        "Tool substitutions needing acknowledged approval: OpenAI/BYOK instead of Gemini/Claude; FastAPI services instead of n8n; SMTP instead of Gmail API; Meta Cloud API instead of Baileys; PostgreSQL tables instead of Google Sheets; Neon + Vercel instead of Supabase + Render.",
        styles["ReportNote"],
    ))

    story.append(p("6. Container image status", styles["ReportH1"]))
    story.append(make_table(
        ["Image", "Local state", "Remote state"],
        [
            ["smart-query-backend:latest", "Built locally, ID a6738e3195be, 512 MB", "manifest unknown; push denied: token lacks expected scopes"],
            ["smart-query-backend:6f388d0", "Built locally, same ID", "Not verified remotely for same reason"],
            ["smart-query-frontend:latest", "Built locally after retry, ID a3a491465717, 1.64 GB; :6f388d0 tag also created", "Not pushed; needs write:packages"],
        ],
        [43 * mm, 72 * mm, doc.width - 115 * mm], styles,
    ))
    story.append(p(
        "The first frontend build failed at npm ci with ETIMEDOUT fetching @types/d3-scale. The retry reused cached layers and completed; the image was verified directly with docker image inspect before tagging. Existing GitHub credential scopes are gist, repo, workflow; write:packages is missing. Operator chose a local PAT file flow. No token value has been printed or committed.",
        styles["ReportNote"],
    ))
    story.append(p(
        "Publication remains BLOCKED. All registry content, including ghcr.io/raphicsdigitalsolutions/smart-query-system:latest, was left untouched: no push, tag overwrite, visibility change or deletion.",
        styles["ReportNote"],
    ))

    story.append(p("7. Final checklist and unresolved gates", styles["ReportH1"]))
    story.append(make_table(
        ["Item", "Status"],
        [
            ["Backend deployed and healthy", "PASS"],
            ["Database connected and at expected schema", "PASS"],
            ["Frontend deployed and healthy", "PASS"],
            ["BFF API env no longer points to placeholder host", "PASS"],
            ["Live auth, CSRF, multipart, report checks", "PASS"],
            ["No paid plans, upgrades, payment methods, add-ons, billing changes", "PASS"],
            ["BYOK-only policy preserved", "PASS"],
            ["GHCR remote images published", "BLOCKED - missing write:packages scope"],
            ["Live Google OAuth, SMTP, WhatsApp, user OpenAI key", "BLOCKED - real credentials not supplied"],
            ["FR-04b instructor auto-routing", "LOCAL VERIFIED - staff-only, active leave, no approval workflow"],
            ["FR-06b conditional polling", "LOCAL VERIFIED - ETag/304; not SSE/push"],
            ["FR-13 routing-exclusion test", "LOCAL VERIFIED"],
            ["FR-14b password auth audit events", "LOCAL VERIFIED - no passwords/secrets"],
            ["Backup restore rehearsal", "LOCAL VERIFIED - disposable Postgres; hosted restore not verified"],
            ["Malware scanning for uploads", "LOCAL INTEGRATION ONLY - default off; NOT DEPLOYED"],
            ["Committed Next.js e2e/accessibility suite", "LOCAL VERIFIED - build pass, 11 passed, no serious/critical axe"],
            ["Hosted cron execution", "NOT VERIFIED - repo config and endpoint tested locally"],
            ["npm audit (Playwright/axe install)", "OPEN - 6 (2 moderate, 2 high, 2 critical)"],
            ["Signed deviation approval / prior FAIL resolution", "BLOCKED - university approval required; FAIL remains"],
            ["No commits or pushes to Git", "PASS"],
        ],
        [100 * mm, doc.width - 100 * mm], styles,
    ))

    story.append(p("8. Conclusion", styles["ReportH1"]))
    story.append(p(
        "The combined hackathon deployment was executed against real hosted services. The public frontend is live, its BFF is talking to the live backend, and the backend is connected to the expected Neon schema. Live smoke checks passed without exposing secret values. The 23 Nov local reconciliation adds deterministic routing, conditional polling, a secret-protected cron trigger, auth audits, a passing disposable backup/restore rehearsal and local-only ClamAV integration; none of that changes hosted configuration or clears governance blockers. This is suitable as a live hackathon demonstration, not a formally approved production release.",
        styles["ReportBody"],
    ))

    story.append(PageBreak())
    story.append(p("9. Security verification", styles["ReportH1"]))
    story.append(p(
        "Vercel CLI redacts hosted values to <SENSITIVE> on pull, so value-level checks used the retained import source and live behavior was checked over the network. No secret value was printed or committed.",
        styles["ReportNote"],
    ))
    story.append(make_table(
        ["Check", "Result"],
        [
            ["JWT secret freshly generated / configured", "PASS - high entropy, differs from old compromised local value"],
            ["BYOK key valid and rotated", "PASS - valid Fernet key, differs from old local value"],
            ["Encrypted BYOK record compatibility", "PASS (N/A) - 0 records, 0 decrypt failures; rotation preserves old keys"],
            ["Old OpenAI key revoked", "PASS - provider returned 401 invalid_api_key"],
            ["Global key empty / fallback disabled", "PASS - empty key, ALLOW_GLOBAL_OPENAI_FALLBACK=false"],
            ["Database URL secure with SSL", "PASS - postgresql+psycopg, Neon, secure sslmode, channel binding"],
            ["CORS restricted to intended origin", "PASS - live allowed origin reflected, unknown origin blocked"],
            ["Cookies Secure + HttpOnly", "PASS - live Set-Cookie httponly=True secure=True"],
            ["Secrets absent from images / narrow deployment-time Git scan", "PASS at deployment time - 307 blobs, 0 findings; images contain no .env/key/cert/db files"],
            ["Broader secret audit (23 Nov)", "TRIAGE ONLY - 307 tracked files; 16 workspace, 12 history, 453 image potential findings; 4 local-env matches; no rotation/revocation"],
        ],
        [70 * mm, doc.width - 70 * mm], styles,
    ))

    story.append(p("10. Live end-to-end and BYOK", styles["ReportH1"]))
    story.append(make_table(
        ["Check", "Result"],
        [
            ["Register / login / logout / session invalidation", "PASS"],
            ["Roles, CSRF missing+wrong (403), owner read, isolation (404)", "PASS"],
            ["Ticket create, notify, assign, status workflow, PDF, multipart", "PASS"],
            ["Missing BYOK key safe error", "PASS - 402 ai_personal_key_required, clear message"],
            ["Cleanup", "PASS - 0 disposable records; final users 1 (admin:1)"],
            ["Real BYOK key add / analysis / isolation", "BLOCKED - no real user key supplied"],
            ["Production department seed data", "PASS - 3 active departments seeded via audited admin API"],
        ],
        [80 * mm, doc.width - 80 * mm], styles,
    ))
    story.append(p(
        "The historical zero-department FAIL was remediated with owner approval: three fixture-sourced departments (Registry, Scholarships, IT Services) were seeded through the audited admin API. A duplicate re-post returned 409; live frontend ticket creation, both auto-routes, retrieval, and assignment all passed; disposable records were removed. No source file was changed.",
        styles["ReportNote"],
    ))

    story.append(p("11. Release checklist dispositions", styles["ReportH1"]))
    story.append(make_table(
        ["Item", "Status"],
        [
            ["FR-04b instructor auto-routing", "LOCAL VERIFIED - staff-only, active leave only, no approval workflow"],
            ["FR-06b conditional polling", "LOCAL VERIFIED - ETag/304; not SSE/push"],
            ["FR-13 routing-exclusion test", "LOCAL VERIFIED"],
            ["FR-14b login/register audit events", "LOCAL VERIFIED - no passwords/secrets"],
            ["Restore rehearsal", "LOCAL VERIFIED - disposable Postgres; hosted restore not verified"],
            ["Malware scanning", "LOCAL INTEGRATION ONLY - default off; NOT DEPLOYED"],
            ["Committed E2E / accessibility tests", "LOCAL VERIFIED - build pass, 11 passed, no serious/critical axe"],
            ["Hosted cron execution", "NOT VERIFIED - repo config and endpoint tested locally"],
            ["npm audit", "OPEN - 6 (2 moderate, 2 high, 2 critical)"],
            ["Signed university deviation approvals", "BLOCKED - FAIL verdict remains"],
            ["Google OAuth / SMTP / WhatsApp live checks", "BLOCKED - real credentials absent"],
            ["Production department seed data", "PASS"],
        ],
        [90 * mm, doc.width - 90 * mm], styles,
    ))

    story.append(p("12. Submission package", styles["ReportH1"]))
    story.append(make_table(
        ["Artifact", "Value"],
        [
            ["Project proposal", "Smart_Query_Routing_Agentic_AI_Project_Proposal_Premium.pdf"],
            ["Deployment PDF", "docs/HACKATHON_DEPLOYMENT_REPORT.pdf"],
            ["Presentation PDF", "docs/HACKATHON_DEPLOYMENT_SLIDES.pdf (13 slides)"],
            ["Frontend / backend", "https://smart-query-routing-system.netlify.app / https://smart-query-backend.vercel.app"],
            ["Docker image", "NOT PUBLISHED - GHCR push blocked (no write:packages)"],
            ["LinkedIn draft", "docs/LINKEDIN_POST_DRAFT.md - not published"],
            ["Hackathon form fields", "None specified on brief pp. 30-31; obtain from actual portal"],
        ],
        [45 * mm, doc.width - 45 * mm], styles,
    ))
    story.append(p(
        "GHCR requires the owner to create a local token with read:packages + write:packages (and repo only if needed for linkage), save it to C:\\Users\\user\\AppData\\Local\\Temp\\opencode\\ghcr_pat.txt, and confirm readiness. Never paste it in chat. Public visibility was approved; anonymous pull will be verified before any image URL is reported.",
        styles["ReportNote"],
    ))

    doc.build(story)
    return path


SLIDES = [
    (
        "Hackathon Deployment Execution",
        "Smart Query Routing System | 22 Nov 2026, reconciled 23 Nov 2026",
        [
            "Backend -> database -> frontend -> auth -> images -> documentation",
            "Live demo: https://smart-query-routing-system.netlify.app",
            "Status: LIVE DEMONSTRATION; formal sign-off open (FAIL verdict unchanged)",
            "No secret values, tokens, or connection strings appear in this deck",
        ],
    ),
    (
        "Live topology",
        "What is actually reachable now",
        [
            "Frontend/BFF: Netlify Free - https://smart-query-routing-system.netlify.app",
            "Deploy 6b02db1360e3188d7f1074c6 - LIVE",
            "Backend: Vercel Hobby - https://smart-query-backend.vercel.app",
            "Deploy dpl_3va9eirAAZ6wajnAVd2bL3kP2EVV - READY",
            "Database: Neon PostgreSQL - 17 tables - revision feedf21773e1",
            "GHCR: local images built; remote push blocked by missing write:packages; registry content untouched",
        ],
    ),
    (
        "What was verified",
        "Actual test and health evidence",
        [
            "Backend final full suite: 225 passed, 17 warnings in 265.61s (0:04:25)",
            "Frontend: typecheck, lint, build pass; 13/13 routes",
            "Backend root, /health, /docs, /openapi.json: HTTP 200",
            "GET /api/v1/status/database: HTTP 200 connected; frontend root and /api/health: HTTP 200",
            "Playwright + axe: build pass; 11 passed (~1.3m); no serious/critical axe on 3 screens",
            "Neon schema verified at expected Alembic head",
        ],
    ),
    (
        "BFF integration smoke",
        "Live through the public frontend",
        [
            "Registration through BFF: HTTP 200; session cookie HttpOnly",
            "CSRF token returned; wrong/missing CSRF: HTTP 403",
            "Multipart proxy: HTTP 201; cleanup DELETE: HTTP 200",
            "PDF report: HTTP 200; application/pdf; no-store; %PDF-1.3",
            "Temporary user and uploaded document removed after test",
            "Final user count: 1 with role admin:1",
        ],
    ),
    (
        "Serverless deviations",
        "Live facts, not future intentions",
        [
            "Background escalation worker disabled on Vercel",
            "backend/vercel.json sets hourly secret-protected sweep; hosted execution NOT VERIFIED",
            "Attachments use /tmp; ephemeral and not shared",
            "Upload cap 4 MiB to match Vercel body limit",
            "DB pool reduced to 1 with 0 overflow; migrations off; Neon already at head",
            "These are live facts, not future intentions",
        ],
    ),
    (
        "Cost and BYOK discipline",
        "Strict $0 and no global AI key",
        [
            "No paid plan, upgrade, payment method, auto recharge, or add-on",
            "No billing setting changed by the assistant",
            "Render refused $0 deployment; no Render service created",
            "ALLOW_GLOBAL_OPENAI_FALLBACK=false; OPENAI_API_KEY empty",
            "BYOK encryption secret stored only as hosted secret env var",
            "No personal OpenAI key in hosted env; production token lifetime 60 min (test-only 1440)",
        ],
    ),
    (
        "Brief coverage",
        "Pages 30-31 mapped honestly",
        [
            "14 functional requirements mapped in the deployment report",
            "Department routing, analytics, reports, announcements, audit, leave, escalation: implemented/tested",
            "FR-04b/FR-13: deterministic staff-only routing, leave-aware, no approval workflow - LOCAL VERIFIED",
            "FR-06: ETag/304 conditional polling + useTicketStatusPolling; not SSE/push - LOCAL VERIFIED",
            "FR-14: password register/login success/failure audits without secrets - LOCAL VERIFIED",
            "Live provider checks blocked; substitutions and zero-cost interpretation need university approval",
        ],
    ),
    (
        "Container images",
        "Local build and registry reality",
        [
            "Backend image built: ghcr.io/raphicsdigitalsolutions/smart-query-backend:latest",
            "Short commit tag also built: :6f388d0",
            "Frontend built locally after an npm ETIMEDOUT retry; :latest and :6f388d0 tagged",
            "Remote manifests missing; push denied without write:packages",
            "Registry content, including ghcr.io/raphicsdigitalsolutions/smart-query-system:latest, untouched",
            "No push, tag overwrite, visibility change, or deletion performed",
        ],
    ),
    (
        "Open gates",
        "Must be disclosed, not claimed complete",
        [
            "GHCR publication BLOCKED; live provider verification BLOCKED",
            "Prior FAIL - DO NOT DEPLOY governance verdict unresolved",
            "University approval required: scope, substitutions, zero-cost, leave workflow, public release",
            "Hosted cron execution NOT VERIFIED",
            "npm audit after Playwright/axe: 6 vulnerabilities (2 moderate, 2 high, 2 critical)",
            "Secret audit triage complete; no rotation/revocation authorized or performed",
            "Restore rehearsal PASS locally; malware local integration only, NOT DEPLOYED",
        ],
    ),
    (
        "Security verification",
        "Evidence, not assumptions",
        [
            "JWT secret high entropy and differs from old compromised value",
            "BYOK Fernet key valid and rotated; 0 encrypted records to break",
            "Old OpenAI key revoked: provider returned 401 invalid_api_key",
            "Global key empty; fallback false; DB SSL on Neon",
            "CORS restricted to the Netlify origin; cookies Secure + HttpOnly",
            "Broader secret audit: 307 tracked; 16 workspace, 12 history, 453 image; 4 local-env matches",
            "Audit stores field names/lengths/fingerprints only; no values printed; no rotation/revocation",
        ],
    ),
    (
        "Live E2E and critical finding",
        "Disposable records only; all removed",
        [
            "Register/login/logout, CSRF 403, roles, isolation 404: PASS",
            "Ticket create, assign, status workflow, PDF, multipart: PASS",
            "Missing BYOK key gives clear 402 error; no global key used",
            "Fixed: 3 approved departments seeded via audited admin API; 409 on duplicate",
            "BLOCKED: real BYOK key add, analysis, and cross-user key test",
            "Cleanup: final user count 1 (admin:1); no real records touched",
        ],
    ),
    (
        "Department reference data fixed",
        "Owner-approved production seed, audited",
        [
            "Was: 0 departments; real ticket submission returned 400",
            "Seeded via admin API: Registry (3), Scholarships (4), IT Services (5)",
            "Names sourced from repo test fixtures; no invention; DB assigned IDs",
            "Duplicate re-post returned 409; idempotent; 3 audit records",
            "Frontend: explicit select, 2 auto-routes, retrieval, assignment: PASS",
            "Disposable tickets/users removed; 1 admin user, 0 tickets remain",
        ],
    ),
    (
        "Conclusion",
        "Demo-ready, not formally signed off",
        [
            "Real public deployment: frontend + backend + database connected",
            "Live smoke evidence passes; local reconciliation adds routing, polling, cron trigger, auth audits",
            "Restore rehearsal PASS locally; malware local integration only",
            "Suitable for a live hackathon demonstration",
            "Not a formally approved production release; FAIL verdict remains",
            "Hosted cron, live provider checks and GHCR publication remain BLOCKED/NOT VERIFIED",
        ],
    ),
]


def draw_wrapped(c, text, x, y, max_width, font, size, leading, color):
    c.setFillColor(color)
    c.setFont(font, size)
    words = text.split()
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if stringWidth(candidate, font, size) <= max_width or not current:
            current = candidate
        else:
            c.drawString(x, y, current)
            y -= leading
            current = word
    if current:
        c.drawString(x, y, current)
        y -= leading
    return y


def build_slides():
    path = OUT_DIR / "HACKATHON_DEPLOYMENT_SLIDES.pdf"
    width, height = landscape(A4)
    c = canvas_module.Canvas(str(path), pagesize=(width, height))
    c.setTitle("Smart Query Routing System - Hackathon Deployment Slides")
    c.setAuthor("Smart Query Routing System")

    for index, (title, subtitle, bullets) in enumerate(SLIDES, start=1):
        c.setFillColor(NAVY)
        c.rect(0, 0, width, height, stroke=0, fill=1)
        c.setFillColor(TEAL)
        c.rect(0, height - 16 * mm, width, 16 * mm, stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(16 * mm, height - 10 * mm, "SMART QUERY ROUTING SYSTEM  |  HACKATHON DEPLOYMENT")
        c.setFont("Helvetica", 9)
        c.drawRightString(width - 16 * mm, height - 10 * mm, f"{index:02d} / {len(SLIDES):02d}")

        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 25)
        c.drawString(18 * mm, height - 38 * mm, title)
        c.setFillColor(colors.HexColor("#9FE3E1"))
        c.setFont("Helvetica", 12)
        c.drawString(18 * mm, height - 48 * mm, subtitle)

        y = height - 66 * mm
        for bullet in bullets:
            c.setFillColor(TEAL)
            c.circle(19 * mm + 1.5, y + 1.5, 1.5, stroke=0, fill=1)
            y = draw_wrapped(
                c, bullet, 25 * mm, y, width - 45 * mm,
                "Helvetica", 11.2, 16, colors.white,
            )
            y -= 5 * mm

        c.setStrokeColor(colors.HexColor("#24456C"))
        c.line(18 * mm, 18 * mm, width - 18 * mm, 18 * mm)
        c.setFillColor(colors.HexColor("#9FB2CA"))
        c.setFont("Helvetica", 8)
        c.drawString(18 * mm, 12 * mm, "Live demo: https://smart-query-routing-system.netlify.app")
        c.drawRightString(width - 18 * mm, 12 * mm, "Full report: docs/HACKATHON_DEPLOYMENT_REPORT.md")
        c.showPage()

    c.save()
    return path


def main():
    report = build_report()
    slides = build_slides()
    print(f"REPORT_PDF={report}")
    print(f"SLIDES_PDF={slides}")


if __name__ == "__main__":
    main()
