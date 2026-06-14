# Tendari (app)

The coach-first CRM that runs your follow-ups for you. Next.js (App Router) + Supabase + Tailwind.

This is the **Phase 0–1 MVP** (functional, offline-capable on just Supabase):
- Marketing landing page on the brand palette.
- Auth + multi-tenant data with Row-Level Security; account auto-provisioned on signup.
- **Contacts**: search, tag filter, inline add, CSV import, detail page (edit, notes timeline,
  tags, that contact's deals + follow-ups).
- **Pipeline**: drag-and-drop board, deal values, per-stage + total sums, won/lost.
- **Follow-ups (tasks)**: due dates, overdue (in the account timezone), complete/delete.
- **Settings**: business name + timezone.
- **Onboarding**: first-run guided walkthrough, interactive getting-started checklist, "How to use" guide.

See `../docs/` for the full plan, specs, pricing and brand identity.

## Quick start

```bash
cd tendari
cp .env.example .env.local          # then fill in your Supabase keys
npm install
npm run dev                         # http://localhost:3000
```

### 1. Create a Supabase project
- Grab `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` from Project Settings → API.
- Run the migrations **in order** in the Supabase SQL editor (or via CLI / MCP):
  `0001_init.sql` → `0002_tasks.sql` → `0003_account_timezone.sql` → `0004_tags.sql`.
  `0001` creates the core tables, RLS policies, and a trigger that provisions an account +
  default pipeline whenever a user signs up.
- For local dev, turn **off** "Confirm email" (Auth → Providers → Email) so signup logs you straight in.

### 2. Run it
- `/` — landing page
- `/signup` → creates your workspace → `/dashboard`
- `/dashboard` — overview + getting-started checklist + "Take the tour"
- `/dashboard/contacts`, `/dashboard/pipeline`, `/dashboard/guide`

## Brand
Logo + palette live in `public/brand/` and `../docs/brand-identity.md`. To use the original PNG logo,
drop it at `public/brand/logo.png`. Colours are wired into `tailwind.config.ts` (forest `#1F6B4C`,
deep-green `#134E37`, sage, mint, canvas).

## Design principles (the differentiator)
- **Ease of use first.** Inline one-line forms, no modals to add a contact or deal, sensible defaults,
  empty states that tell you exactly what to do next.
- **Guided onboarding.** A first-run walkthrough (`components/onboarding-tour.tsx`), an interactive
  checklist, and a "How to use" page — replayable any time.
- **Calm, on-brand aesthetic.** One tight palette, generous whitespace, soft shadows, rounded shapes.

## Deploy (Netlify / Vercel)
- Set the two `NEXT_PUBLIC_SUPABASE_*` env vars (+ `NEXT_PUBLIC_SITE_URL`).
- Vercel: import the repo, set root to `tendari/`. Netlify: use the Next.js runtime, base dir `tendari/`.
- The automation engine (Phase 3) will run on Supabase (pg_cron + pgmq), not on the web host — see
  `../docs/specs/automation-engine.md`.

## Roadmap
Next up per `../docs/specs/mvp-roadmap.md`: booking → Google Calendar, email + automation engine,
Stripe payments, forms/contracts, usage metering.
