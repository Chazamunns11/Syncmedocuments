# Tend — Automation Engine Spec

The automation engine is the **moat** — it's what makes Tend "GHL-style" rather than a contact list.
This document specifies triggers, actions, the runner, and reliability rules.

---

## 1. Concept
A **workflow** = a `trigger` + an ordered list of `steps`. When a trigger fires for a contact, a
`workflow_run` is created at step 0. A **worker** (Supabase pg_cron + pgmq) advances each run: it
executes the current step and either moves to the next immediately or sets `next_run_at` for a wait.

This `workflow_runs` + `next_run_at` + cron-worker pattern is the entire secret to "wait 3 days, then
email." It avoids the Netlify/Vercel limitation (their cron is recurring-only and can't run delayed
per-task jobs).

## 2. Triggers
| Trigger | Fires when |
|---|---|
| `contact_created` | new contact added (any source) |
| `tag_added` / `tag_removed` | tag changes on a contact |
| `stage_changed` | deal moves to a stage (filter by target stage) |
| `form_submitted` | a form is submitted (filter by form) |
| `booking_created` / `booking_cancelled` / `booking_completed` / `no_show` | booking lifecycle |
| `payment_succeeded` / `invoice_paid` | money received |
| `contract_signed` | contract e-signed |
| `email_opened` / `email_clicked` / `email_replied` | email engagement |
| `sms_replied` | inbound SMS (v1.1) |
| `webhook_received` | inbound webhook from an external app (filter by source) |
| `date_based` | scheduled relative to a contact date field (e.g. birthday, renewal) |

Trigger config: `{ type, filters: {...} }`. Filters narrow firing (e.g. `stage_changed` where
`stage = 'Proposal'`).

## 3. Actions / step types
| Step type | Config | Notes |
|---|---|---|
| `send_email` | template_id or inline subject/body | merge fields; metered |
| `send_sms` (v1.1) | body | metered; respects quiet hours + opt-out |
| `wait` | duration (minutes/hours/days) **or** until-time-of-day | sets `next_run_at` |
| `add_tag` / `remove_tag` | tag | |
| `move_stage` | pipeline_id, stage_id | |
| `create_task` / `notify` | message, channel (in-app/email/Slack) | internal alert |
| `webhook` | url, payload template | **outbound integration** — Zapier/Make compatible |
| `ai_draft` (v1.1) | prompt, target (email draft) | proposes; human approves before send |
| `condition` / `branch` | predicate over contact/context | if/else → different step paths |
| `goal` / `exit` | predicate | exit run early if goal met (e.g. booked a call) |

## 4. The runner (worker)
**Schedule:** pg_cron every 60s (can go to seconds if needed; keep jobs <10 min).

**Loop (pseudo):**
```sql
-- claim due runs (skip-locked for concurrency safety)
SELECT * FROM workflow_runs
 WHERE status='waiting' AND next_run_at <= now()
 ORDER BY next_run_at
 LIMIT 100
 FOR UPDATE SKIP LOCKED;
```
For each claimed run:
1. Load workflow definition + current step.
2. Execute step:
   - **action** → perform (send/move/tag/webhook/notify), write `workflow_step_log`, increment
     `current_step`, set `status='active'` to process next step immediately (loop).
   - **wait** → compute `next_run_at`, set `status='waiting'`, stop.
   - **condition/branch** → evaluate, jump `current_step` to the chosen branch.
   - **exit/goal met** → `status='completed'`.
3. On last step → `status='completed'`.
4. On error → retry policy (below); after max retries → `status='failed'` + dead-letter + notify owner.

For long/external actions (email/SMS/AI) enqueue to **pgmq** and let a consumer perform the side-effect,
so the cron tick stays fast and within timeout limits (mind Supabase's ~10-min job + pg_net call
timeouts noted in research).

## 5. Reliability rules (non-negotiable)
- **Idempotency:** every send carries an idempotency key (`run_id:step_id`). Re-processing never
  double-sends.
- **One active run per (workflow, contact):** unique partial index — re-triggering doesn't stack
  duplicate sequences (matches the "at most once" discipline coaches expect).
- **Retries:** exponential backoff (e.g. 1m, 5m, 30m, 2h) up to N; then dead-letter + alert.
- **Suppression & caps:** respect unsubscribe/opt-out suppression list and per-account spend caps before
  any send; if capped, pause the run and notify owner rather than fail.
- **Quiet hours / timezone:** schedule sends in the contact's (or account's) timezone; SMS respects quiet
  hours and STOP.
- **Audit:** `workflow_step_log` records every step outcome.

## 6. Booking slot algorithm (the other real piece of logic)
Not part of the engine but the other genuinely algorithmic bit — spec'd here for completeness:
1. Generate candidate slots from `availability_rules` for the requested date range (respect duration,
   buffer, min-notice, max-per-day), in the account timezone.
2. Fetch busy intervals from Google Calendar freebusy.
3. Subtract busy ∪ existing `bookings`; drop slots violating buffer/min-notice/max-per-day.
4. Return free slots in the **booker's** timezone.
- **Must be unit-tested** with DST edges, overlapping busy blocks, and buffer boundaries.

## 7. Starter workflow templates (ship these on day one)
- **New lead nurture:** `contact_created` → send welcome → wait 2d → if not booked, send "book a call"
  → wait 3d → reminder → exit on `booking_created`.
- **Booking reminders:** `booking_created` → confirmation → wait until 24h before → reminder →
  wait until 1h before → reminder.
- **No-show recovery:** `no_show` → "sorry we missed you, rebook" email.
- **Post-payment onboarding:** `payment_succeeded` → welcome + intake form → contract → wait 1d → kickoff.
- **Re-engagement:** `date_based` (no activity 30d) → check-in email.

## 8. Testing
- Pure-function tests for: step state transitions, wait computation, condition evaluation, idempotency.
- Integration tests for: trigger→run creation, worker advancing a run with a wait, suppression/cap halts.
- e2e: form submit → nurture sequence fires → email sent (sandbox) → goal exit on booking.
