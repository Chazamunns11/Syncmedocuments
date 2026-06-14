# Tendril — Technical Specification

Master spec for the Tendril coach-first CRM. Companion docs:
`data-model.md`, `automation-engine.md`, `mvp-roadmap.md`.

---

## 1. Product scope (what we're building)
A multi-tenant SaaS web app where a coach manages contacts, a sales/client pipeline, bookings,
payments, contracts/forms, and **automated email/SMS follow-ups**, with optional AI assistance.

**v1 (MVP) modules:** Auth/accounts · Contacts · Pipeline (Kanban) · Booking → Google Calendar ·
Payments/invoicing (Stripe) · Forms & contracts · Email + automation engine · Session notes/timeline ·
Inbound/outbound webhooks · Usage metering + spend caps.

**Deferred:** SMS, AI assist, public API, native Gmail/Slack connectors, import tools, Studio/team,
white-label.

**Out of scope (deliberately — this is the anti-bloat stance):** white-label SaaS resale, sub-accounts,
agency reporting, lead scoring, full LMS/course builder, community spaces, missed-call text-back,
reputation/review management, heavy funnel builder.

---

## 2. Architecture
```
                ┌───────────────── Web app (Next.js, React) ─────────────────┐
                │  Pipeline · Contact/timeline · Booking page · Forms ·       │
                │  Automation builder · Settings/integrations · Usage meter   │
                └───────────────┬─────────────────────────────────────────────┘
                                │  (API routes / server actions; Supabase client)
        ┌───────────────────────┼───────────────────────────┐
        │                       │                            │
   Supabase                Automation worker            Integration layer
   (Postgres + Auth        (pg_cron + pgmq queue)       Email: Resend/Postmark
    + RLS + Storage)       advances workflow_runs       Calendar: Google
   all tenant data         where next_run_at<=now()     Payments: Stripe
   + usage ledger          fires actions, retries       SMS: Twilio (v1.1)
                                                          AI: Claude API / MCP (v1.1)
                                                          Inbound webhooks: /hooks/*
                                                          Outbound: "call webhook" action
```

### 2.1 Recommended stack
- **Frontend + API:** Next.js (App Router) on **Vercel or Netlify**. Server actions / route handlers
  for API. (Per research: Netlify/Vercel are great for UI + webhooks but **cannot** run delayed
  automation workers alone.)
- **Data + auth + automation engine:** **Supabase** — Postgres, Auth, Row-Level Security (multi-tenant),
  Storage (files/contracts), **pg_cron + pgmq** for the durable "wait then send" worker. Already wired
  into this session via Supabase MCP.
- **Email:** Resend (cheapest at low scale) or Postmark (premium deliverability). Domain auth required.
- **Payments:** Stripe (Checkout + Billing for our own subscriptions; Connect or direct keys for the
  coach's client payments — **no surcharge**).
- **Calendar:** Google Calendar API (OAuth).
- **SMS (v1.1):** Twilio. **AI (v1.1):** Claude API via Agent SDK, CRM actions exposed as an MCP server.

**Why not Netlify/Vercel alone:** their cron is recurring-only isolated invocations and they can't run
persistent background workers — delayed automations need Supabase pg_cron+pgmq (chosen) or
Cloudflare Durable Object Alarms / a Render worker (alternatives).

### 2.2 Multi-tenancy
- Every domain table carries `account_id`. **Postgres RLS** enforces isolation: a user can only read/write
  rows where `account_id` matches their JWT claim. This is the single most important security control —
  get it right before anything else.
- An `account` = one coaching business; `users` belong to an account (1 for Solo/Pro, up to 5 for Studio).

---

## 3. Module specs

### 3.1 Auth & accounts
- Supabase Auth (email/password + Google OAuth). Magic-link optional.
- On signup → create `account` + `user` + default `pipeline` with starter stages + start trial.
- Trial: 14 days, card captured via Stripe at signup (opt-out trial).
- Roles: `owner`, `member` (Studio). Billing actions = owner only.

### 3.2 Contacts
- CRUD; fields: name, email, phone, tags, source, custom fields (JSONB), timezone, notes.
- Each contact has a **unified timeline** (`activities`): emails, SMS, bookings, payments, notes,
  stage changes, form submissions, automation events.
- Bulk import (CSV) — and a v2 importer for GHL/Practice/Kajabi exports.
- Dedup on email; merge tool (v2).

### 3.3 Pipeline (Kanban)
- `pipelines` → `stages` (ordered) → `deals` (a contact in a stage with value, status).
- Drag-and-drop between stages; moving a deal emits a `stage_changed` event (automation trigger).
- Default coach pipeline: *Lead → Discovery Call → Proposal → Active Client → Renewal → Past*.

### 3.4 Booking → Google Calendar
- Coach connects Google Calendar (OAuth, store refresh token in `integrations`).
- Coach defines **availability rules** (weekly windows, buffer, min notice, max/day, meeting types
  with duration/price).
- Public page `/{account-slug}/book/{meeting-type}`:
  1. Read busy times from Google (freebusy), subtract from availability → free slots.
  2. Booker picks slot + fills intake form.
  3. Create Google Calendar event (+ Meet link), create `booking` + `contact` if new.
  4. Emit `booking_created` trigger (→ confirmation email + reminder sequence).
- Reminders via the automation engine (e.g. 24h + 1h before). Reschedule/cancel links.
- **Slot-math is the only real algorithmic work** — see `automation-engine.md` note + tests required.

### 3.5 Payments / invoicing (Stripe, no surcharge)
- Coach connects **their own Stripe** (Stripe Connect Standard, or their API keys). Money flows
  coach→client directly; **Tendril takes no payment surcharge** (key differentiator vs Kajabi).
- Features: one-off invoices, payment links, package/subscription products, checkout embedded in
  booking flow. Webhook from Stripe → log payment to contact timeline, emit `payment_succeeded` trigger.
- Separately, Stripe Billing handles **Tendril's own subscription** (Solo/Pro/Studio) + metered overage.

### 3.6 Forms & contracts
- Form builder (fields → JSONB schema). Public form pages; submission → contact + `form_submission`
  activity + `form_submitted` trigger.
- Contracts: templated docs with merge fields + e-signature (typed/drawn). Store signed PDF in Supabase
  Storage. `contract_signed` trigger.

### 3.7 Email + automation engine
- Transactional + sequence email via Resend/Postmark. Templates with merge fields ({{first_name}} etc.).
- Open/click tracking → `email_opened` / `email_clicked` triggers.
- **Inbound email** (replies) via provider inbound webhook → thread onto contact timeline.
- Full engine spec in `automation-engine.md`.

### 3.8 Session notes / timeline
- Free-text + structured notes per contact/session; pinned to timeline. (Optional v1.1: AI call summary.)

### 3.9 Integrations ("link into other apps")
Three layers — **build the bus, not many connectors**:
1. **Inbound webhooks:** generic `POST /hooks/{account_token}/{source}` → normalized into events that
   can trigger automations (forms, Stripe, Typeform, Zapier, etc.).
2. **Outbound:** a **"call webhook"** automation action → instant Zapier/Make compatibility.
3. **Native connectors (added one at a time):** Google Calendar (v1), Stripe (v1), then Gmail, Slack,
   Twilio. Long tail handled by webhooks + Zapier.

### 3.10 Usage metering & spend caps (anti-bill-shock)
- `usage_ledger` records every billable event (email send, SMS segment, AI tokens) with cost.
- Per-account **daily + monthly spend caps** (configurable, default on). When near cap → warn; at cap →
  pause sends, notify owner.
- **Usage dashboard:** live this-period consumption vs included allowance + projected overage.

### 3.11 AI assist (v1.1, optional)
- Claude (Agent SDK) drafts follow-ups, summarizes calls/notes, suggests next actions.
- CRM actions exposed via a small **MCP server** (`find_contact`, `log_note`, `draft_email`, …).
- **Human-in-the-loop on all writes/sends** — agent proposes, coach approves. Permission-gated
  (PreToolUse) — never auto-send. Metered as AI credits.

---

## 4. Security, privacy, compliance
- **Tenant isolation:** Postgres RLS on every table (non-negotiable, day one).
- **Card data:** never touches our servers — Stripe Checkout/Elements only (PCI SAQ-A).
- **Secrets:** integration tokens encrypted at rest; per-account scoping.
- **Email compliance:** SPF/DKIM/DMARC, one-click unsubscribe, suppression list, sending-domain auth.
- **SMS compliance:** A2P 10DLC registration, STOP/opt-out handling, quiet hours.
- **GDPR/UK-GDPR:** data export + delete per contact and per account; DPA; privacy policy; EU data
  region option (Supabase region choice).
- **AI safety:** human approval on writes; log all agent actions; no training on customer data.
- **Auditability:** `webhook_events` + `usage_ledger` + activity log give a full trail.

## 5. Non-functional requirements
- **Reliability of automations:** idempotency keys on every send; retries w/ backoff; dead-letter queue;
  "never message the same contact twice for the same step" guard.
- **Performance:** pipeline board + contact list paginated; slot computation cached per day.
- **Observability:** structured logs, error tracking (Sentry), Stripe + provider webhook dashboards.
- **Backups:** Supabase PITR; periodic logical exports.
- **Testing:** unit (slot math, devig of overrides, automation step transitions), integration (webhooks),
  e2e (signup→book→pay→automation fires).

## 6. Environments & config
- `local` (Supabase local stack), `staging`, `production` (separate Supabase projects).
- Secrets via env: `SUPABASE_*`, `STRIPE_*`, `GOOGLE_OAUTH_*`, `RESEND_API_KEY`/`POSTMARK_*`,
  `TWILIO_*`, `ANTHROPIC_API_KEY`.
- Built and maintained with **Claude Code** (on the web sessions operate on the committed repo;
  the live app is hosted separately on Vercel/Netlify + Supabase — Claude Code builds it, doesn't run it).
