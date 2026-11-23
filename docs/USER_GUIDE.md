# User Guide — Smart Query Routing System

This guide explains how students, staff, heads of department (HODs), and administrators use the system. Availability of some features depends on your role and on external providers configured by your deployment team (SMTP email, Meta WhatsApp, Google OAuth2, and personal OpenAI keys). If a menu item or button is missing, it is not enabled for your role or build.

> A live hackathon deployment now exists at `https://smart-query-routing-system.netlify.app`, backed by the Vercel-hosted API and Neon database. Provider features still require real accounts and exact configuration before they work. See `docs/HACKATHON_DEPLOYMENT_REPORT.md`.

## 1. Roles at a glance

| Role | Typical user | Main capabilities |
| --- | --- | --- |
| **Student** | Enrolled student | Register/sign in, submit and track tickets, reply publicly, view own history and announcements |
| **Staff** | Advisor / support officer | Work assigned tickets, publish public replies, add internal notes, use AI assistance, update allowed statuses |
| **HOD** | Head of department | Everything staff can do, plus department-wide visibility, assignment/priority/status overrides, escalation, knowledge approval, department-scoped analytics, and leave management |
| **Admin** | System administrator | Everything HOD can do, plus departments and users, global analytics/reports, audit log, knowledge management, all announcements |

Role assignments are controlled by the backend. Public self-registration always creates a **student** account; it cannot grant staff/HOD/admin rights.

## 2. Signing in and account access

### Password sign-in

1. Open the application URL and choose **Sign in**.
2. Enter your university email and password.
3. New students choose **Create an account** (name, email, password of at least 12 characters).
4. Staff/HOD/admin accounts are provisioned by an administrator or a local provisioning CLI; there are no default credentials.

### Google sign-in (only when configured)

If your deployment enabled Google OAuth2, the sign-in page also offers **Continue with Google**. This build uses Google Identity Services: Google returns a credential to the browser, which posts it to the application's same-origin BFF route for server-side verification. There is no application redirect callback URI. The same role-based permissions apply; Google identity does not grant extra access.

Your deployment must have registered the exact JavaScript origin and configured both the backend `GOOGLE_OAUTH_CLIENT_ID` and the frontend `NEXT_PUBLIC_GOOGLE_CLIENT_ID`, then rebuilt the frontend. If Google sign-in is absent or fails, use password sign-in and contact your administrator.

### Session and security notes

- Your session is stored in an `HttpOnly`, `SameSite=Lax`, `Secure` (HTTPS) cookie. It is never available to JavaScript in the browser.
- Sessions expire after 60 minutes by default in production; sign in again when prompted. The automated test environment uses a longer lifetime (1440 minutes) only for test stability; that value is not a deployed setting.
- Use **Sign out** on shared devices.
- Never share your password or personal API key.

## 3. Submitting a query (ticket)

1. Go to **New query / Submit ticket** from your role home page.
2. Enter a clear subject and full description. Choose the relevant department/category where offered.
3. Include all relevant detail in the description. You can attach PDF, TXT or MD files (5 MiB default) to a ticket; each upload creates a linked message. Administrators can also upload governed knowledge documents through the knowledge page.
4. Submit. You receive a unique public reference number — keep it for follow-up.

### Auto-routing and channels

- The system determines the target department and priority from your selection and available routing information; AI recommendations may assist staff but are advisory. Instructor assignment is deterministic and staff-only: an active `staff` user in the department with the lowest open-ticket load is chosen (stable name/ID tie-breaks). HODs and admins are never auto-assigned, staff inside an active leave window are excluded, and there is no in-app approval step for auto-assignment. If nobody is eligible, the query stays `new` for manual assignment.
- Submitted queries are recorded with their **channel**: web form, email, or WhatsApp. Email/webhook and WhatsApp submission work only if those integrations were configured by your deployment. Otherwise the web form is the supported channel.
- If you submit by email or WhatsApp, use the university-approved address/number and include enough detail for routing. Delivery/intake confirmations depend on provider setup.

## 4. Tracking status and history

Open **My queries** (students) or the ticket list for your role. Select a ticket to see its conversation, history, assignee, department, priority, and status.

Statuses, in lifecycle order:

| Status | Meaning |
| --- | --- |
| `new` | Received, awaiting assignment |
| `assigned` | Assigned to a staff member |
| `in_progress` | Actively being worked on |
| `waiting_for_student` | The team needs your reply |
| `resolved` | A resolution has been provided |
| `closed` | Final state; no further changes |

- Status and assignment changes are recorded in the ticket history with actor and time. Deterministic
  auto-routing assigns an available instructor immediately; if nobody is eligible, the ticket stays in
  `new` for an HOD or admin to assign manually.
- Queries not resolved within the configured SLA (24 hours by default) are flagged overdue/escalated when the sweep runs. A secret-protected cron trigger is configured in the repository, but live hosted cron execution has not been verified. Notifications depend on deployment configuration.
- The ticket detail view polls a small status snapshot about every 15 seconds using a conditional GET
  (ETag/304). This is polling, not SSE or push messaging; a 304 response means nothing changed.
- HODs and admins can override routing, priority, status, and assignment; overrides are audited.

## 5. Conversations, public replies, and internal notes

- **Public replies** are visible to the student and are eligible for email/WhatsApp notification.
- **Internal notes** are visible only to staff/HOD/admin. Students never see them, and they are never emailed or sent through WhatsApp.
- **Attachments** (PDF, TXT or MD, 5 MiB default) can be uploaded from the ticket detail page. Each upload creates a linked message; internal uploads follow the same privacy rule as internal notes. File bytes are stored outside the database, and only safe metadata is displayed.
- Staff may reply and move tickets through operational statuses. Reopening to `new` and escalation are HOD/admin actions.

## 6. AI assistance panel (staff and above)

The AI panel helps staff classify queries, suggest departments/assignees, retrieve approved knowledge, and draft a reply.

Rules you must know:

1. **Personal key required in production.** Each user who wants AI assistance must add their own OpenAI API key in account settings. The key is encrypted at rest, scoped to that user, and never shown in the browser again after entry. Under the production policy there is no global/admin fallback key. If no key is configured, the panel will tell you to add one; AI will not silently use someone else's key.
2. **Approval gate.** AI drafts are suggestions only. Nothing is posted publicly or emailed until you review it and select **Approve / Publish**. Approval is recorded in the audit trail. Unapproved drafts are never sent to students.
3. **Approved knowledge only.** Drafts may cite only knowledge documents that an HOD/admin has approved. If no approved source supports an answer, the assistant should abstain rather than invent one.
4. **Limits apply.** Input/output tokens, retries, timeouts, recursion depth, and a per-user rate limit keep runs bounded. Exceeding the limit produces a clear error.
5. **Privacy.** Ticket content used in AI runs is redacted where configured; secrets are not logged. You remain responsible for reviewing accuracy and appropriateness before publishing.

## 7. Knowledge management (HOD / Admin)

Approved knowledge is the only material the assistant may cite.

- Upload PDF or text/Markdown documents within the configured size/type limits.
- Documents are versioned. Review content, then **approve** it; unapproved or deactivated documents are never retrieved.
- HODs manage knowledge for their department; admins may manage across departments.
- Changing a document creates a new version so previous citations remain traceable.
- If a menu item is absent, your role lacks permission or the Phase 7 knowledge UI is not present in your build.

## 8. Analytics and reports (Admin)

The admin area provides aggregate views of query volume, status/priority mix, departmental load, SLA/escalation indicators, and response activity.

- Export reports to PDF or Excel where the export controls are present in your build.
- Use filters (date range, department, status) before exporting.
- Figures are generated from live ticket and audit data; exports are a point-in-time snapshot and may contain personally identifiable information — store them accordingly.

## 9. Announcements (Admin / HOD)

- Admins may broadcast announcements to selected audiences (for example all students, a department, or a role).
- HODs may broadcast within their department where permitted.
- Students see announcements relevant to them in their workspace. Announcements are informational; they do not replace a ticket.

## 10. Instructor leave and auto-reply

Staff members who are instructors can mark themselves as on leave / unavailable and, where enabled, set an auto-reply message.

- Automatic routing excludes staff whose active leave window covers the current time (the end time is
  exclusive). Manual assignment by an HOD or admin remains available and still publishes the instructor's auto-reply.
- Auto-replies apply to incoming queries assigned to that instructor. There is no in-app approval workflow for routing or the auto-reply; the leave rules/workflow still require university approval as an unresolved scope deviation.
- Always set a return date and update availability when you return. HODs/admins can review leave information for their area.

## 11. Notifications

When the deployment has configured notifications, you may receive in-app notifications and/or email (and WhatsApp for the WhatsApp channel) for:

- Ticket submitted
- Ticket assigned
- Public reply posted
- Escalation / De-escalation / SLA breach (to authorized assigned staff, department HODs, and admins; SLA auto-sweep also notifies the student)
- Ticket resolved

Privacy rules:

- Internal notes and unapproved AI drafts are **never** notified.
- Notifications contain only the minimum context needed; open the application to see full details.
- If email/WhatsApp is not configured, in-app history remains available, and no external messages are sent. SMTP/Meta failures do not block ticket operations.

## 12. Audit and history

- Each ticket keeps status, assignment, escalation/de-escalation, and message history with timestamps, previous/new states, and actors.
- Admins can view system-wide audit entries where the audit UI is present in your build.
- AI analysis, approval, routing overrides, escalation/de-escalation, and password registration/login outcomes (success and failure) are recorded. Auth audit rows carry email/context, never a password or API key.
- Audit records are intended for accountability; do not alter or delete them.

## 13. Privacy and data rules

- Access is role-scoped: students see only their own tickets; staff see assigned/eligible tickets; HODs see their department; admins see across the system.
- Internal notes are hidden from students.
- Personal OpenAI keys are encrypted at rest, never returned to the browser, never logged, and never used for another user.
- Secrets (database, SMTP, Meta, JWT, encryption keys) live only in server-side environment/secret storage.
- External providers receive only data needed for the feature you use (OAuth identity, email address for SMTP, message content for WhatsApp, redacted ticket content for AI).
- Report exports and attachments may contain personal data: handle them under your institution's retention and privacy policy.

## 14. Getting help

Check the dashboard **Backend status** card first. If it shows offline, contact your administrator with the ticket reference and the time of the failure. administrators should follow `docs/DEPLOYMENT_GUIDE.md` for health checks, backups, and provider configuration.

University approval is still outstanding for scope deviations, tool/model/hosting substitutions, the zero-cost interpretation, the leave workflow, and release/public governance; the prior `FAIL — DO NOT DEPLOY` verdict remains in force. The live hackathon deployment is a demonstration, not an approved production release. *(Updated 2026-11-24: local Next.js 16.4.6 / Zod 4.6.7 security upgrades verified end-to-end with 0 npm vulnerabilities, 229 backend tests, and 12 Playwright/Axe checks passing.)*
