# LinkedIn post draft — Smart Query Routing System

**Status: DRAFT ONLY. Do not publish without owner approval.**

---

Excited to share the live hackathon deployment of the **Smart Query Routing System** — a role-based university communication hub that classifies student queries, routes them to the right department, and gives staff AI-assisted drafting and full status tracking.

**What is live now**
- Frontend + Next.js BFF: https://smart-query-routing-system.netlify.app
- FastAPI backend: https://smart-query-backend.vercel.app
- PostgreSQL: Neon, connected and migrated

**Verified in the live system**
- Registration, login, logout, HttpOnly + Secure sessions, CSRF rejection
- Ticket creation, assignment, status workflow, PDF export, multipart upload
- Cross-user isolation, notification records, role-based access
- BYOK-only AI policy: no global platform OpenAI key; missing personal keys produce a clear, safe error

**Built with** FastAPI, PostgreSQL/Neon, Next.js, Vercel, Netlify, and per-user BYOK OpenAI keys — on free tiers, with no paid services.

This is a live hackathon demonstration. Formal production sign-off and live Google/SMTP/WhatsApp provider verification are still in progress, and I'm keeping those gates explicit rather than claiming them done.

Supervisor: Saima Jamil

#Hackathon #SmartQueryRouting #FastAPI #Next.js #PostgreSQL #AI #FreeTier

---

## Pre-publication checklist (owner to confirm)

- [ ] Owner approves this wording.
- [ ] GHCR image URL is added only after the image is actually published and anonymous pull is verified.
- [ ] No secrets, tokens, connection strings, or private URLs are included.
- [ ] Any remaining university-required approval is obtained before publication if the brief requires it.
