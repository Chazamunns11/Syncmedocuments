# Tendari — MVP Build Roadmap

Sequenced so each phase ships something demoable and de-risks the hard parts early.
Built and maintained with Claude Code. Target: solo founder + AI, lean managed services.

---

## Phase 0 — Foundations (week 1)
- [ ] Supabase project (staging + prod), Next.js app scaffold, deploy to Vercel/Netlify.
- [ ] Auth (Supabase Auth: email + Google), accounts + users tables, **RLS on every table**.
- [ ] Tenant model + a cross-tenant isolation test (must return zero rows).
- [ ] CI: `supabase db` migrations, type generation, lint, tests. SessionStart hook keeps web sessions green.
**Exit:** a user can sign up, an account+default pipeline is created, data is tenant-isolated.

## Phase 1 — CRM core (week 1–2)  *(the easy 80%)*
- [ ] Contacts CRUD + tags + custom fields + CSV import.
- [ ] Pipeline Kanban (stages, drag-drop deals) → emits `stage_changed`.
- [ ] Contact timeline (`activities`) rendering notes + events.
**Exit:** coach can manage contacts and a visual pipeline. Demoable.

## Phase 2 — Booking (week 2–3)  *(visible, de-risks slot math)*
- [ ] Google Calendar OAuth + token storage.
- [ ] Meeting types + availability rules.
- [ ] Public booking page; slot algorithm (unit-tested, DST edges).
- [ ] Create Google event + Meet link; `booking` + `booking_created` event.
**Exit:** a prospect books a real slot; it lands on the coach's Google Calendar.

## Phase 3 — Email + Automation engine (week 3–5)  *(the moat — hardest 20%)*
- [ ] Resend/Postmark integration + domain auth (SPF/DKIM/DMARC) + suppression list.
- [ ] Email templates + merge fields; open/click tracking; inbound reply → timeline.
- [ ] `workflows` + `workflow_runs` schema; pg_cron + pgmq worker.
- [ ] Triggers: contact_created, tag_added, stage_changed, booking_created, form_submitted.
- [ ] Actions: send_email, wait, add/remove_tag, move_stage, notify, webhook.
- [ ] Idempotency, retries, dead-letter, one-run-per-contact guard.
- [ ] Ship 5 starter templates.
**Exit:** "wait 3 days then email" works reliably end-to-end; booking reminders fire.

## Phase 4 — Payments + Forms/Contracts (week 5–6)
- [ ] Stripe Connect (coach's own Stripe, **no surcharge**) — invoices, payment links, products.
- [ ] Stripe webhooks → `payment_succeeded`/`invoice_paid` triggers + timeline.
- [ ] Form builder + public forms → `form_submitted`.
- [ ] Contract templates + e-signature + signed PDF storage → `contract_signed`.
**Exit:** coach can get paid and onboard a client without leaving Tendari.

## Phase 5 — Billing, metering, launch-ready (week 6–7)
- [ ] Stripe Billing for **Tendari's own** subscription (Solo/Pro/Studio) + trial + founder coupon.
- [ ] `usage_ledger` + spend caps + usage dashboard (anti-bill-shock).
- [ ] Inbound webhook bus `/hooks/*`; outbound webhook action hardened.
- [ ] Settings/integrations UI; data export/delete (GDPR).
- [ ] Error tracking (Sentry), backups (PITR), privacy policy/ToS.
**Exit:** can charge customers; bill-shock controls live. **MVP shippable.**

---

## Post-MVP
### v1.1 — Differentiators
- [ ] SMS (Twilio) + 10DLC registration + STOP/quiet hours; SMS actions in engine.
- [ ] AI assist (Claude Agent SDK + CRM MCP server): draft follow-ups, summarize calls, suggest
      actions — **human-approved only**, metered as AI credits.
- [ ] Migration importers (Practice.do, GHL, Kajabi exports).

### v2 — Scale
- [ ] Studio/team (multi-seat, roles), white-label booking page.
- [ ] Public API + API keys.
- [ ] Native connectors: Gmail, Slack, Zapier app.
- [ ] Reporting dashboard (revenue, pipeline, CLV-style cohort views).

---

## Build principles
- **Narrow ruthlessly** — every "GHL also has X" is a reason to *not* build X (see anti-bloat list in
  technical-spec §1). Win by being the coach-first tool that does ~7 things well.
- **De-risk early** — automation engine + slot math + deliverability are the only hard parts; tackle
  them in phases 2–3, not last.
- **Managed services over custom infra** — Supabase/Stripe/Resend/Google do the heavy lifting.
- **Tests stay green** — pure-function tests for slot math + engine transitions; keep the suite offline.
- **Human-in-the-loop AI** — never auto-send; permission-gate agent writes.

## First commit checklist (when coding starts)
1. Supabase migrations for tenancy + contacts + pipeline.
2. RLS policies + isolation test.
3. Next.js auth + signup flow.
4. Contacts + pipeline UI.
5. Type generation wired into CI.
