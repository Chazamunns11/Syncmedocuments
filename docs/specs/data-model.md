# Tendril — Data Model

Postgres (Supabase). Every tenant table carries `account_id` and is protected by **Row-Level Security**.
Types are indicative; timestamps are `timestamptz`; ids are `uuid` (default `gen_random_uuid()`).

---

## Core tenancy
```
accounts
  id, name, slug (unique, for booking URLs), plan ('solo'|'pro'|'studio'),
  trial_ends_at, stripe_customer_id, stripe_subscription_id, status, timezone, created_at

users
  id (= auth.users.id), account_id -> accounts, email, name, role ('owner'|'member'), created_at
```

## Contacts & pipeline
```
contacts
  id, account_id, first_name, last_name, email, phone, timezone, source,
  custom_fields jsonb, created_at, updated_at
  -- unique (account_id, lower(email))

tags
  id, account_id, name, color
contact_tags
  contact_id, tag_id   (PK both)

pipelines
  id, account_id, name, is_default
stages
  id, pipeline_id, name, position, is_won, is_lost
deals
  id, account_id, contact_id, pipeline_id, stage_id, title, value_cents,
  currency, status ('open'|'won'|'lost'), created_at, updated_at
```

## Timeline / activities
```
activities          -- unified contact timeline
  id, account_id, contact_id, type
     ('note'|'email'|'sms'|'booking'|'payment'|'stage_change'
      |'form_submission'|'contract'|'automation'|'webhook'),
  title, body, meta jsonb, created_at, created_by

notes               -- (or fold into activities.type='note')
  id, account_id, contact_id, body, created_by, created_at
```

## Messaging
```
messages            -- email + sms, in + out
  id, account_id, contact_id, channel ('email'|'sms'), direction ('in'|'out'),
  subject, body, status ('queued'|'sent'|'delivered'|'opened'|'clicked'|'bounced'|'failed'),
  provider_id, thread_id, opened_at, clicked_at, created_at

email_templates
  id, account_id, name, subject, body, created_at
```

## Booking
```
meeting_types
  id, account_id, name, slug, duration_min, price_cents, location_type
     ('google_meet'|'phone'|'in_person'|'custom'), description, active

availability_rules
  id, account_id, weekday (0-6), start_time, end_time, buffer_min,
  min_notice_min, max_per_day

bookings
  id, account_id, contact_id, meeting_type_id, starts_at, ends_at, status
     ('confirmed'|'cancelled'|'completed'|'no_show'),
  google_event_id, meet_url, intake jsonb, created_at
```

## Payments
```
products            -- coach's offerings sold to their clients
  id, account_id, name, price_cents, currency, recurring ('none'|'monthly'|'yearly'),
  stripe_price_id, active

invoices
  id, account_id, contact_id, amount_cents, currency, status
     ('draft'|'sent'|'paid'|'void'), stripe_invoice_id, due_at, paid_at, created_at

payments
  id, account_id, contact_id, amount_cents, currency, stripe_payment_intent_id,
  status, created_at
```

## Forms & contracts
```
forms
  id, account_id, name, slug, schema jsonb, active
form_submissions
  id, account_id, form_id, contact_id, data jsonb, created_at

contract_templates
  id, account_id, name, body, merge_fields jsonb
contracts
  id, account_id, contact_id, template_id, status ('sent'|'signed'|'void'),
  signed_pdf_url, signed_at, created_at
```

## Automation engine  (full behaviour in automation-engine.md)
```
workflows
  id, account_id, name, trigger jsonb, steps jsonb, active, created_at, updated_at
     -- trigger: { type, filters }
     -- steps:   ordered array of { id, type, config }

workflow_runs
  id, account_id, workflow_id, contact_id,
  current_step int, status ('active'|'waiting'|'completed'|'cancelled'|'failed'),
  next_run_at timestamptz,           -- index this: WHERE status='waiting' AND next_run_at<=now()
  context jsonb, idempotency_key, created_at, updated_at
     -- unique (workflow_id, contact_id) when active  -> "one run per contact per workflow"

workflow_step_log
  id, run_id, step_id, status ('done'|'skipped'|'failed'), detail jsonb, created_at
```

## Integrations, usage, webhooks
```
integrations
  id, account_id, provider ('google'|'stripe'|'twilio'|'resend'|'slack'|'gmail'),
  access_token (encrypted), refresh_token (encrypted), scopes, meta jsonb,
  status, connected_at

webhook_endpoints       -- outbound targets the coach configures
  id, account_id, url, secret, events text[], active

webhook_events          -- inbound + audit (idempotency)
  id, account_id, source, external_id, payload jsonb, processed_at, created_at
     -- unique (source, external_id)  -> idempotent inbound

usage_ledger            -- every billable unit, for metering + caps
  id, account_id, kind ('email'|'sms'|'ai_tokens'), quantity, cost_cents,
  ref_id, created_at

spend_caps
  account_id (PK), daily_cap_cents, monthly_cap_cents, paused boolean
```

---

## Key indexes & constraints
- `workflow_runs (status, next_run_at)` — the hot path for the worker.
- `activities (account_id, contact_id, created_at desc)` — timeline render.
- `contacts (account_id, lower(email))` unique — dedup.
- `webhook_events (source, external_id)` unique — inbound idempotency.
- RLS policy on **every** table: `account_id = auth.jwt() ->> 'account_id'` (via a claim or a
  `user→account` lookup). Verify with tests that cross-tenant reads return zero rows.

## Generated types
Use Supabase `generate_typescript_types` (MCP) to keep the TS client types in sync after each migration.
