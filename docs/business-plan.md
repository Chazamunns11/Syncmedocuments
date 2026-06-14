# Tend — Business Plan

> **Working name: Tend** — "the coach-first CRM that runs your follow-ups for you."
> Alternates if `tend.coach` / trademark is taken: **Roster**, **Cadence**, **Caseload**.
> *(Domain + trademark availability NOT yet verified — do this before committing to branding.)*

---

## 1. One-line pitch
A simple, flat-priced CRM built **for solo online coaches** — pipeline, booking, payments,
contracts, and automated follow-ups in one tool — without GoHighLevel's agency bloat,
surprise usage bills, or 2–4 week learning curve.

## 2. The problem (evidence-backed)
Online coaches are stuck between two bad options:

- **All-in-one platforms (GoHighLevel, Kajabi)** are powerful but **agency-shaped, bloated,
  and meter usage** → "$97" bills arrive at ~$140, email deliverability is weak (GHL/Mailgun),
  and onboarding takes 2–4 weeks. Coaches "use less than half of what they pay for."
- **Coach-native tools (Paperbell, Simply.Coach, CoachAccountable)** are simple but
  **feature-thin** — no real automation engine, weak/no SMS, no integration bus.

There is a genuine gap: **a coach-first CRM with a real automation engine and clean
integrations, at transparent flat pricing.** Reinforced by **Practice.do shutting down
(Nov 2025)**, leaving customers looking for a home.

## 3. Target customer (ICP)
- **Primary:** solo online coaches (business / life / fitness / health) doing **$30k–$150k/yr**,
  managing 10–80 clients, currently juggling Calendly + Stripe + a spreadsheet, or unhappy on GHL/Kajabi.
- **Secondary:** small coaching practices (2–5 coaches) — the "Studio" tier.
- **Explicitly NOT:** agencies/resellers (that's GHL's game and a different product). We win by being
  narrow and coach-first.

Market reality (2025 ICF study): coaches average ~$72k/yr; bottom 10% under $30k → **price sensitivity
is real**, spend clusters **under $100/mo**, hard balk at the **$100–150** line.

## 4. Positioning & differentiation
| vs. | Their weakness | Tend's edge |
|---|---|---|
| GoHighLevel | Agency bloat, usage bill-shock, learning curve, weak deliverability | Coach-first, flat pricing w/ included allowances + spend caps, setup in a day, deliverability-first email |
| Kajabi | $149 entry, course-first, Stripe surcharge, light CRM | $29 entry, CRM-first, **no payment surcharge / no lock-in** |
| Paperbell / Simply.Coach | No real automation, no SMS, no integrations | Real automation engine + SMS + webhook integration bus |
| DIY (Calendly+Stripe+Sheets) | Disconnected, manual follow-up | One tool, automated follow-ups, one timeline per client |

**Three sharp promises:** (1) *No bill shock* — generous bundles, at-cost overage, hard spend caps,
live usage meter. (2) *Own your data & payments* — direct Stripe, no surcharge, easy export.
(3) *Set up in a day, not a month.*

**AI angle (optional, differentiating):** a built-in Claude-powered assistant that **drafts**
follow-ups, summarizes calls, and proposes next actions — human-approved, never auto-sent.

## 5. Pricing (see `docs/pricing.md` for full rationale)
- **Solo $29/mo** · **Pro $69/mo** (target tier ⭐) · **Studio $149/mo**
- 14-day free trial (card required). Annual = 2 months free.
- **Founder deal:** first 50–100 customers locked at **$19/mo for life** for testimonials + traction.

## 6. Go-to-market
1. **Founder/beta phase (months 0–3):** recruit 20–50 design-partner coaches from communities
   (coach Facebook groups, Skool communities, r/lifecoaching, X/LinkedIn coach circles). Free →
   founder pricing. Goal: PMF signal + testimonials.
2. **Migration play (months 2–6):** target **Practice.do refugees** and **GHL-frustrated coaches**
   with a "switch in a day" import tool + concierge onboarding.
3. **Content + SEO:** comparison content ("GHL alternative for coaches", "Practice.do alternative",
   "Kajabi too expensive"), automation templates, deliverability guides.
4. **Partnerships:** coach-certification bodies, coach-school communities, affiliate program (coaches
   refer coaches — flat referral, not a white-label reseller scheme).
5. **Product-led:** booking page is a public, branded acquisition surface ("Powered by Tend").

## 7. Financial model (illustrative)
- **Infra baseline:** ~$0 at MVP (free tiers) → ~$150–250/mo once live (Supabase Pro + hosting + email).
- **Gross margin:** ~80%+ on the CRM; SMS/email/AI priced as at-cost-overage credits to protect margin.
- **Variable COGS per customer (Pro tier, typical):** email ~$2–5, AI ~$1–4, SMS pass-through.
- **MRR milestones** (blended ~$60 ARPU):
  - $1k MRR ≈ 17 customers · $5k ≈ 85 · **$10k ≈ ~145 Pro customers** · $30k ≈ ~430.
- **Unit economics target:** keep CAC low via content/community (not paid ads initially); annual
  billing for cash flow; aim LTV:CAC > 3 within 12 months.

## 8. Roadmap (high level — see `docs/specs/mvp-roadmap.md`)
- **MVP (v1):** contacts + pipeline, booking → Google Calendar, Stripe payments, forms/contracts,
  email automation engine, session notes, webhooks.
- **v1.1:** SMS (Twilio), AI assist (Claude drafts), usage dashboard + spend caps.
- **v2:** team/Studio tier, public API, native integrations (Gmail, Slack, Zapier), import tools.

## 9. Risks & mitigations
- **Email deliverability** (the thing that sinks competitors) → use Resend/Postmark, enforce domain
  auth (SPF/DKIM/DMARC), warm-up, opt-out handling. Treat as a first-class feature, not plumbing.
- **Automation reliability** (double-sends, missed waits) → idempotency keys, durable queue, retries,
  dead-letter handling, "never message twice" guards.
- **Crowded $97 band** → don't compete there; own the **$29–69 coach-first** lane.
- **Solo-founder bandwidth** → narrow scope ruthlessly; lean on managed services + Claude Code to build.
- **Compliance** (PII + payments + SMS) → Stripe handles card data; RLS for tenant isolation;
  10DLC registration for SMS; clear privacy policy + data export/delete.
- **AI write-safety** → human-in-the-loop on all sends; permission-gated agent actions.

## 10. Why now
Practice.do's shutdown, GHL fatigue, Kajabi's price hikes, deliverability complaints, and the
maturity of cheap building blocks (Supabase, Resend, Stripe, Claude Agent SDK/MCP) make a focused,
coach-first CRM both **needed** and **cheap to build** in 2026.

---
*Sources & full research: `docs/pricing.md` and the deep-research syntheses in session history.
Pricing/competitor figures verified 2025–2026 but several came from secondary sources — re-verify
live before publishing any comparison page.*
