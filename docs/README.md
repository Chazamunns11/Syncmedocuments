# Tend — Coach-first CRM (planning & specs)

Planning docs for **Tend**, a simple, flat-priced GoHighLevel/Practice.do alternative built
specifically for solo online coaches. *(Name is provisional — see business plan.)*

> Note: this lives in the `Syncmedocuments` repo alongside an unrelated value-betting bot.
> These are planning/spec documents only — no Tend application code has been written yet.

## Documents
- **[business-plan.md](business-plan.md)** — name, problem, ICP, positioning, GTM, financials, risks.
- **[pricing.md](pricing.md)** — recommended tiers ($29 / $69 / $149), rationale, anti-bill-shock model,
  unit costs, competitive landscape.
- **[unit-economics.md](unit-economics.md)** — cost to run, profit per customer (~$59/Pro/mo, ~85% margin),
  fixed costs by stage, MRR milestones.
- **[branding.md](branding.md)** — naming research, name shortlist (lead candidate **Tendril**;
  backups Grove, Lodestar), and a finalize-the-name checklist (domain + UK/US trademark).
- **specs/**
  - **[technical-spec.md](specs/technical-spec.md)** — architecture, stack, modules, security, NFRs.
  - **[data-model.md](specs/data-model.md)** — Postgres schema (Supabase + RLS).
  - **[automation-engine.md](specs/automation-engine.md)** — triggers, actions, the runner, reliability.
  - **[mvp-roadmap.md](specs/mvp-roadmap.md)** — phased build plan (7 weeks to MVP).

## TL;DR
- **Gap:** coach-native CRMs are too thin; all-in-ones (GHL/Kajabi) are bloated, metered, agency-shaped.
  Practice.do shut down Nov 2025. There's room for a coach-first CRM with a real automation engine at
  flat pricing.
- **Stack:** Next.js (Vercel/Netlify) + Supabase (Postgres/Auth/RLS + pg_cron+pgmq automation worker) +
  Stripe (no surcharge) + Google Calendar + Resend/Postmark; later Twilio + Claude AI assist.
- **Moat:** the automation engine (`workflow_runs` + `next_run_at` + cron worker) and no-bill-shock
  pricing (bundled allowances + at-cost overage + hard spend caps).
- **Pricing:** Solo $29 / **Pro $69** ⭐ / Studio $149; 14-day card-required trial; founder deal $19/life.

## Research provenance
Figures come from a multi-source deep-research pass (2025–2026). Several competitor prices/stats came
from secondary sources because vendor pages blocked automated fetch — **re-verify live before publishing
any public comparison.**
