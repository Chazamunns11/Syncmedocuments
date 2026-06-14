# Tendril — Pricing Strategy & Research

*Synthesis of deep research (2025–2026). Method caveat: many vendor pages 403'd to automated
fetch, so a number of figures come from search-result extracts / secondary sources. Hard tier
prices are more reliable; willingness-to-pay and churn figures are directional. Re-verify live
before publishing comparisons.*

---

## Recommended pricing

| Tier | Monthly | Annual (2 mo free) | For | Key inclusions |
|---|---|---|---|---|
| **Solo** | **$29** | $290 | New / bootstrapped coaches | CRM + pipeline · booking · payments (no surcharge) · forms/contracts · email automation · 1 user · ~1,000 contacts · 2,000 emails/mo · light AI drafts |
| **Pro** ⭐ | **$69** | $690 | Working coaches *(target / anchor tier)* | Everything in Solo **+** SMS · full automation engine · unlimited contacts · 10,000 emails/mo · more AI credits · webhooks · integrations |
| **Studio** | **$149** | $1,490 | Coaches with a team / practice | Everything **+** up to 5 seats · white-label booking page · API access · priority support · larger allowances |

**Trial:** 14-day free trial, **credit card required** (opt-out trials convert ~31% vs ~9% no-card).
**No permanent freemium** — high support cost, low conversion for a solo founder.
**Founder deal:** first 50–100 customers locked at **$19/mo for life** (or capped LTD) to seed
traction + testimonials; grandfather as prices rise.

### Why these numbers
- **Pro at $69** sits **under the $100–150 psychological balk line** for solo coaches, while being
  ~2x the value of thin coach-native tools (Paperbell $57, Simply.Coach $57) and far below GHL/Kajabi.
- **3 tiers** because ~60–70% of buyers pick the middle (anchoring + center-stage effect); Studio
  anchors Pro as the reasonable choice.
- **Flat, not per-seat** — per-seat punishes adoption of a primarily single-user tool.
- **Launch at value, not cheap** — the #1 bootstrapper mistake is underpricing 50–200%. $29–99 is the
  band where micro-SaaS reaches $5k MRR fastest. Easier to lower than raise.
- **Annual framed as "2 months free"** (~17%) — improves cash flow + ~30% lower churn than monthly.

### MRR math (blended ~$60 ARPU)
$1k ≈ 17 customers · $5k ≈ 85 · **$10k ≈ ~145** · $30k ≈ ~430.
Full cost-to-run and profit-per-customer breakdown: **`unit-economics.md`** (Pro ≈ $59 profit/mo, ~85%).

---

## Anti-"bill-shock" model (core differentiator vs GoHighLevel)
GHL's metered SMS/email is the #1 source of bill-shock complaints. Tendril's rule: **bundle generous
allowances, pass overage through at/near cost, ship hard spend caps + a live usage meter.**

- **Included in each tier:** a generous email allowance + (Pro+) an SMS/AI credit pool.
- **Overage:** billed transparently at **near cost** (no GHL-style stacked markup). GHL itself removed
  its 5% markup (Oct 2025) — match or beat that.
- **Hard daily spend caps** per account (configurable) + a **usage dashboard** = the combination that
  actually kills bill-shock complaints.
- **Credits as abstraction:** one credit currency for SMS/email/AI lets you re-cost silently when
  vendor prices move.

### Your unit costs (verified ~2026, re-check — these move fast)
| Item | Cost to you |
|---|---|
| Twilio SMS (US, all-in incl. A2P) | ~$0.013–0.014 / segment |
| Twilio US number | ~$1.15/mo (toll-free ~$2.15) |
| A2P 10DLC registration | Sole-prop/low-vol brand ~$4.50; standard ~$46; campaign vetting ~$15; + ~$1.50–10/mo per campaign |
| Resend email | Free 3k/mo; Pro $20 = 50k; overage ~$0.90/1,000 |
| Postmark email | $15 = 10k; overage $1.20–1.80/1,000 (premium deliverability) |
| Claude API (per M tokens) | Haiku 4.5 ~$1 in / $5 out · Sonnet 4.6 ~$3 / $15 · Opus 4.8 ~$5 / $25 |

**AI cost levers:** output costs 5x input; use Haiku for drafts, batch (−50%) + prompt caching (−~90%)
where possible. Don't hardcode token economics — Haiku's price has moved.
**Email path:** Resend is cheapest at low scale; Postmark if deliverability needs the premium.

---

## Competitive pricing landscape (2025–2026, for reference)
| Tool | Tiers | Shape |
|---|---|---|
| GoHighLevel | $97 / $297 / $497 | All-in-one, **usage-metered**, agency-first, white-label |
| Kajabi | ~$149 / $199 / $399 | Course-first, contact-capped, **Stripe surcharge** |
| Skool | $9 / $99 | Community + courses only (no CRM/booking) |
| HoneyBook | $29 / $49 / $109 | Service-biz CRM, payments+contracts (reported big 2025 hike) |
| Dubsado | $20 / $40 | Creative CRM, deep automation, steep curve |
| Paperbell | $57 / $97 (~$47.50 annual) | Coach-native, simple, light automation |
| Simply.Coach | from $57 flat | Coach-native CRM |
| CoachAccountable | ~$20 → $80 | Scales with active clients |
| Systeme.io | Free / $17 / $47 / $97 | Budget all-in-one, contact-capped |
| ActiveCampaign | $15–79 @1k contacts | Email/automation, **scales with list size** |
| **Practice.do** | — | **Shut down Nov 2025** (migration opportunity) |

**Gap Tendril fills:** coach-native CRM + booking + payments + contracts **with** a real automation
engine + SMS + integrations, at **flat, non-metered, non-contact-capped** pricing.

---

## Open decisions to confirm
- Exact included allowances per tier (email/SMS/AI) — set once infra costs are measured in beta.
- Whether AI assist is bundled into Pro or a paid add-on credit pack.
- Studio seat count and white-label scope.
- Founder-deal cap (50 vs 100) and whether lifetime vs 1-year locked.
