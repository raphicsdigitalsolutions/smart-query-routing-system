"""Generate the final hackathon deployment report and slide-deck PDFs.

Run from the repository root:
    .\\backend\\.venv\\Scripts\\python.exe docs\\generate_hackathon_deployment_pdfs.py

The script uses only reportlab and writes no secret material. All facts are
reconciled against the 2026-11-24 release evidence in docs/evidence/.
"""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageBreak,
    PageTemplate,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs"

NAVY = colors.HexColor("#0B1F3A")
TEAL = colors.HexColor("#0E9F9F")
CANVAS = colors.HexColor("#F5F7FA")
MUTED = colors.HexColor("#526279")
GREEN = colors.HexColor("#1E7F5C")
AMBER = colors.HexColor("#B7791F")
RED = colors.HexColor("#B42318")

DIGEST = "sha256:2cf0a5dea54dffd643abf29a1fa7b72966899ff7235350b95fe1da793c9c2177"
COMMIT = "2cb5595ee7a38c85c63223079dc9d17a290ed089"
VERCEL_DEPLOY = "dpl_CRo9kXq4CBL8p8oSaaAyKdSjNVoM"


def styles_report():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        "TitleX", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=21, leading=26, textColor=NAVY, spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        "SubX", parent=styles["Normal"], fontName="Helvetica",
        fontSize=9.5, leading=13, textColor=MUTED, spaceAfter=10,
    ))
    styles.add(ParagraphStyle(
        "H1X", parent=styles["Heading1"], fontName="Helvetica-Bold",
        fontSize=13, leading=17, textColor=NAVY, spaceBefore=10, spaceAfter=5,
    ))
    styles.add(ParagraphStyle(
        "H2X", parent=styles["Heading2"], fontName="Helvetica-Bold",
        fontSize=10.5, leading=14, textColor=TEAL, spaceBefore=7, spaceAfter=3,
    ))
    styles.add(ParagraphStyle(
        "BodyX", parent=styles["BodyText"], fontName="Helvetica",
        fontSize=8.8, leading=12, textColor=colors.HexColor("#172033"),
        alignment=TA_LEFT, spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        "CellX", parent=styles["BodyText"], fontName="Helvetica",
        fontSize=7.4, leading=9.6, textColor=colors.HexColor("#172033"),
    ))
    styles.add(ParagraphStyle(
        "CellHeadX", parent=styles["BodyText"], fontName="Helvetica-Bold",
        fontSize=7.6, leading=9.8, textColor=colors.white,
    ))
    styles.add(ParagraphStyle(
        "BulletX", parent=styles["BodyText"], fontName="Helvetica",
        fontSize=8.8, leading=12, leftIndent=11, bulletIndent=2,
        textColor=colors.HexColor("#172033"), spaceAfter=2,
    ))
    return styles


def p(text, style):
    return Paragraph(str(text), style)


def table(headers, rows, widths, styles):
    data = [[p(h, styles["CellHeadX"]) for h in headers]]
    data.extend([p(c, styles["CellX"]) for c in row] for row in rows)
    t = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
    ]
    for i in range(1, len(data)):
        if i % 2 == 0:
            style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#EEF3F8")))
    t.setStyle(TableStyle(style))
    return t


def banner(text, styles, fill="#FFF6E5", border=AMBER, style_name="BodyX"):
    t = Table([[p(text, styles[style_name])]], colWidths=[170 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(fill)),
        ("BOX", (0, 0), (-1, -1), 0.8, border),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def on_page(canvas, doc):
    canvas.saveState()
    width, height = A4
    canvas.setFillColor(NAVY)
    canvas.rect(0, height - 11 * mm, width, 11 * mm, stroke=0, fill=1)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(18 * mm, height - 7.5 * mm, "SMART QUERY ROUTING SYSTEM")
    canvas.drawRightString(width - 18 * mm, height - 7.5 * mm, "FINAL HACKATHON DEPLOYMENT REPORT")
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 7.3)
    canvas.drawString(18 * mm, 9 * mm, "24 Nov 2026 | Technical release verified; formal sign-off open")
    canvas.drawRightString(width - 18 * mm, 9 * mm, f"Page {doc.page}")
    canvas.restoreState()


def build_report():
    path = OUT_DIR / "HACKATHON_DEPLOYMENT_REPORT.pdf"
    doc = BaseDocTemplate(
        str(path), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=17 * mm, bottomMargin=17 * mm,
        title="Smart Query Routing System - Final Hackathon Deployment Report",
        author="Smart Query Routing System",
    )
    doc.addPageTemplates([PageTemplate(
        id="all",
        frames=[Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")],
        onPage=on_page,
    )])
    s = styles_report()
    story = []

    story.append(p("Final Hackathon Deployment Report", s["TitleX"]))
    story.append(p(
        "Smart Query Routing System | reconciled 24 Nov 2026 | GitHub, Vercel, Neon release-v1, Netlify, Docker Hub",
        s["SubX"],
    ))
    story.append(banner(
        "Technical release artifacts are published and verified. Formal institutional/governance "
        "approval, live provider verification, hosted cron invocation, and confirmed Netlify source "
        "sync remain NOT VERIFIED. This is a verified hackathon demonstration, not an approved "
        "production release.", s,
    ))
    story.append(Spacer(1, 7))

    story.append(p("1. Executive status", s["H1X"]))
    story.append(table(
        ["Area", "Verified status"],
        [
            ["GitHub", f"origin/main {COMMIT}; clean tree after release evidence commits"],
            ["Backend API (Vercel)", f"READY production deployment {VERCEL_DEPLOY}; aliases live"],
            ["Cron configuration", "One daily cron at 0 0 * * *; Hobby-compatible; hosted invocation not verified"],
            ["Database (Neon)", "release-v1 read-only PASS: 17 tables, 4 departments, 0 users, 0 tickets, no writes"],
            ["Frontend (Netlify)", "Public root and /api/health HTTP 200; authenticated deploy state and source sync NOT VERIFIED"],
            ["Docker Hub", f"latest and v1.0.0 published at {DIGEST}; anonymous pull verified"],
            ["Test suite", "Backend 229 passed; Playwright + axe 12 passed; Vitest 3 passed; lint/typecheck/build PASS"],
            ["Security audit", "npm audit and npm audit --omit=dev: 0 vulnerabilities; no secrets printed or staged"],
            ["Governance", "University approval and live OAuth/SMTP/WhatsApp/BYOK checks NOT VERIFIED"],
        ],
        [34 * mm, 136 * mm], s,
    ))

    story.append(p("2. Release topology", s["H1X"]))
    story.append(table(
        ["Layer", "Endpoint / identifier", "State"],
        [
            ["Frontend + BFF", "https://smart-query-routing-system.netlify.app", "Public HTTP 200; deploy sync unconfirmed"],
            ["Backend API", "https://smart-query-backend.vercel.app", f"READY; {VERCEL_DEPLOY}"],
            ["Database", "Neon PostgreSQL release-v1", "Read-only verified; original production DB checked read-only earlier, not modified"],
            ["Container", "raphicsdigitalsolutions/smart-query-system", f"latest and v1.0.0 at {DIGEST}"],
        ],
        [27 * mm, 72 * mm, 71 * mm], s,
    ))

    story.append(p("3. Quality and security evidence", s["H1X"]))
    story.append(table(
        ["Check", "Result"],
        [
            ["Backend pytest", "229 passed, 17 pre-existing LangSmith warnings in 410.30s (0:06:50)"],
            ["Vitest / lint / typecheck", "3 passed; lint PASS; typecheck PASS"],
            ["Next.js build", "PASS - Next.js 16.4.6 webpack, 12/12 static pages"],
            ["Playwright + axe", "12 passed in 2.0m; no serious/critical violations on scanned pages"],
            ["npm audit", "0 vulnerabilities for all dependencies and production-only dependencies"],
            ["Docker / Compose", "Both Compose configs valid; docker build --check no warnings"],
            ["Alembic", "head/current feedf21773e1; alembic check clean"],
            ["Live backend smoke", "health, status and DB readiness HTTP 200; departments HTTP 401 expected"],
        ],
        [42 * mm, 128 * mm], s,
    ))

    story.append(p("4. Database isolation (release-v1)", s["H1X"]))
    story.append(table(
        ["Field", "Read-only result"],
        [
            ["Database", "neondb"],
            ["URL fingerprint (SHA-256, 12)", "5d1fc726d19b"],
            ["Host fingerprint (SHA-256, 12)", "141f6064ec7f"],
            ["Alembic revision", "feedf21773e1"],
            ["Public tables", "17"],
            ["Departments / users / tickets", "4 / 0 / 0"],
            ["Writes", "none"],
        ],
        [55 * mm, 115 * mm], s,
    ))
    story.append(p(
        "Branch identity is taken from the operator-provided git-ignored backend/.env.release_v1 "
        "file name. Vercel withholds sensitive DATABASE_URL values and the Neon UI session was "
        "unavailable, so direct Vercel-to-file equality is not claimed. The original production "
        "database was previously checked read-only and not modified; this release-v1 check did not "
        "re-check it.",
        s["BodyX"],
    ))

    story.append(p("5. Docker release", s["H1X"]))
    story.append(table(
        ["Item", "Result"],
        [
            ["Repository", "raphicsdigitalsolutions/smart-query-system"],
            ["Tags", "latest and v1.0.0, same digest"],
            ["Digest", DIGEST],
            ["Anonymous pull", "PASS - temporary empty Docker config, exit 0; registry manifest HTTP 200"],
            ["Container", "healthy; UID 10001; Supervisor backend + frontend RUNNING"],
            ["HTTP smoke", "backend health, frontend login, frontend API health and session all HTTP 200"],
            ["Hygiene", "0 .env files, 0 key files in image; no production connection used"],
        ],
        [34 * mm, 136 * mm], s,
    ))

    story.append(p("6. Verified limitations and manual actions", s["H1X"]))
    for text in [
        "Netlify owner: confirm the production deploy and redeploy from GitHub main if the live Turbopack build is not the intended source; no deploy was changed during verification.",
        "Hosted FR-07 cron: the daily schedule is verified, but an actual hosted invocation and escalation effect were not observed.",
        "Live providers: Google OAuth, SMTP, Meta WhatsApp and real-user OpenAI BYOK were not exercised against real accounts.",
        "Governance: signed university approval for scope/tool/hosting deviations remains outstanding.",
        "Operations: hosted restore, deployed malware scanner, monitoring and retention were not verified.",
    ]:
        story.append(Paragraph(text, s["BulletX"], bulletText="•"))

    story.append(p("7. Evidence index", s["H1X"]))
    story.append(table(
        ["Artifact", "Purpose"],
        [
            ["phase1_release_audit_2026-11-24.json", "Git, deployment and cron audit"],
            ["phase2_quality_verification_2026-11-24.json", "Tests, build, audit, DB and live smoke"],
            ["phase4_docker_hub_release_2026-11-24.json", "Docker Hub tags, digest, container smoke"],
            ["phase5_live_verification_2026-11-24.json", "Vercel, Netlify and release-v1 live status"],
            ["release_v1_readonly_verification_2026-11-24.json", "Read-only database counts and schema"],
            ["docker_hub_anonymous_pull_2026-11-24.json", "Anonymous pull verification"],
        ],
        [72 * mm, 98 * mm], s,
    ))

    doc.build(story)
    return path


def on_slide(canvas, doc):
    width, height = landscape(A4)
    canvas.saveState()
    canvas.setFillColor(NAVY)
    canvas.rect(0, height - 12 * mm, width, 12 * mm, stroke=0, fill=1)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(14 * mm, height - 8 * mm, "SMART QUERY ROUTING SYSTEM")
    canvas.drawRightString(width - 14 * mm, height - 8 * mm, "FINAL HACKATHON DEPLOYMENT")
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(14 * mm, 8 * mm, "24 Nov 2026 | Verified release evidence")
    canvas.drawRightString(width - 14 * mm, 8 * mm, f"Slide {doc.page}")
    canvas.restoreState()


def slide_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        "SlideTitle", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=24, leading=29, textColor=NAVY, spaceAfter=10,
    ))
    styles.add(ParagraphStyle(
        "SlideBody", parent=styles["BodyText"], fontName="Helvetica",
        fontSize=12, leading=17, textColor=colors.HexColor("#172033"),
    ))
    styles.add(ParagraphStyle(
        "SlideCell", parent=styles["BodyText"], fontName="Helvetica",
        fontSize=10, leading=14, textColor=colors.HexColor("#172033"),
    ))
    styles.add(ParagraphStyle(
        "SlideHead", parent=styles["BodyText"], fontName="Helvetica-Bold",
        fontSize=10, leading=14, textColor=colors.white,
    ))
    return styles


def slide_table(headers, rows, widths, s):
    data = [[p(h, s["SlideHead"]) for h in headers]]
    data.extend([p(c, s["SlideCell"]) for c in row] for row in rows)
    t = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def build_slides():
    path = OUT_DIR / "HACKATHON_DEPLOYMENT_SLIDES.pdf"
    doc = BaseDocTemplate(
        str(path), pagesize=landscape(A4), leftMargin=14 * mm, rightMargin=14 * mm,
        topMargin=17 * mm, bottomMargin=15 * mm,
        title="Smart Query Routing System - Final Hackathon Deployment Slides",
        author="Smart Query Routing System",
    )
    doc.addPageTemplates([PageTemplate(
        id="all",
        frames=[Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")],
        onPage=on_slide,
    )])
    s = slide_styles()
    story = []

    story.append(p("Technical Release Verified", s["SlideTitle"]))
    story.append(banner(
        "GitHub main 2cb5595 | Vercel READY | Neon release-v1 verified | Docker Hub published | "
        "Netlify public site live; source sync unconfirmed | Formal sign-off open", s,
        style_name="SlideBody",
    ))
    story.append(Spacer(1, 12))
    story.append(slide_table(
        ["Layer", "Verified state"],
        [
            ["Backend", f"Vercel production {VERCEL_DEPLOY}; health/status/DB readiness HTTP 200"],
            ["Cron", "One daily schedule 0 0 * * *; invocation not observed"],
            ["Database", "release-v1: 17 tables, 4 departments, 0 users, 0 tickets; no writes"],
            ["Frontend", "Netlify public root and /api/health HTTP 200; deploy state unauthenticated"],
            ["Container", f"latest and v1.0.0 at {DIGEST}; anonymous pull verified"],
        ],
        [38 * mm, 225 * mm], s,
    ))
    story.append(PageBreak())

    story.append(p("Verification Summary", s["SlideTitle"]))
    story.append(slide_table(
        ["Area", "Result"],
        [
            ["Backend tests", "229 passed, 17 pre-existing warnings in 0:06:50"],
            ["Frontend tests", "Vitest 3 passed; Playwright + axe 12 passed in 2.0m"],
            ["Build and types", "Next.js 16.4.6 webpack build, 12/12 pages; lint/typecheck PASS"],
            ["Security", "npm audit and prod-only audit: 0 vulnerabilities"],
            ["Docker", "healthy container, UID 10001, Supervisor running both services, 4 HTTP 200 checks"],
            ["Database", "Alembic feedf21773e1; release-v1 counts 4/0/0; no writes"],
        ],
        [45 * mm, 218 * mm], s,
    ))
    story.append(PageBreak())

    story.append(p("Open Items - Do Not Overstate", s["SlideTitle"]))
    story.append(slide_table(
        ["Item", "Status / action"],
        [
            ["Netlify source sync", "NOT VERIFIED - owner confirms deploy; redeploy from main if needed"],
            ["Hosted cron", "Schedule verified; real invocation/escalation effect NOT VERIFIED"],
            ["Live providers", "Google OAuth, SMTP, Meta WhatsApp, real-user BYOK NOT VERIFIED"],
            ["Governance", "Signed university approval for deviations NOT VERIFIED"],
            ["Operations", "Hosted restore, malware scanner, monitoring and retention NOT VERIFIED"],
        ],
        [45 * mm, 218 * mm], s,
    ))
    story.append(Spacer(1, 10))
    story.append(p(
        "Live demo: https://smart-query-routing-system.netlify.app | "
        "Backend: https://smart-query-backend.vercel.app", s["SlideBody"],
    ))

    doc.build(story)
    return path


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in (build_report(), build_slides()):
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
