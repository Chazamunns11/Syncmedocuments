# Tendril — Unit Economics

What it costs to run Tendril and the profit per customer. Built from cost figures verified in the
2025–2026 deep research (see `pricing.md`). **Estimates** — re-measure against real usage in beta.

> Scope: these are **operating COGS and gross margin**. They exclude the founder's time/salary,
> customer-acquisition cost (CAC), and one-off setup costs (listed at the bottom).

---

## 1. Variable cost per customer / month
What it costs to serve one coach:

| Cost | Solo (light) | Pro (typical, w/ SMS) |
|---|---|---|
| Email (Resend, ~$0.90/1k sends) | ~$1 | ~$2 |
| AI drafts (Claude Haiku) | ~$0.50 | ~$1.50 |
| SMS + phone number (Twilio, if used) | $0 | ~$4 |
| Stripe fee on **our** subscription (2.9% + 30¢) | ~$1.15 | ~$2.30 |
| **Total COGS / customer** | **~$3** | **~$10** |

> The coach's **client** payments flow through the coach's **own** Stripe (no surcharge), so that
> isn't our cost. Only collecting *our* subscription fee incurs Stripe fees for us.

## 2. Profit per customer / month
| Tier | Price | COGS | **Gross profit** | Margin |
|---|---|---|---|---|
| **Solo** | $29 | ~$3 | **~$26** | ~90% |
| **Pro** ⭐ | $69 | ~$10 | **~$59** | ~85% |
| **Studio** | $149 | ~$25 | **~$124** | ~83% |
| Founder ($19/life) | $19 | ~$6 | **~$13** | ~68% |

Healthy vs the SaaS benchmark (75–85%). Heavy SMS/AI is the margin eroder — which is exactly why
those are metered as at-cost credits with hard spend caps (see `pricing.md` anti-bill-shock model).

## 3. Fixed platform cost (regardless of customer count)
| Stage | Fixed cost/mo | Notes |
|---|---|---|
| **Dev / pre-launch** | **~$0–50** | Free tiers: Supabase, Netlify, Resend free |
| **Early (~10–25 customers)** | **~$55–100** | Supabase Pro $25 + Resend Pro $20 + monitoring + domains |
| **At $10k MRR (~150 customers)** | **~$300** | Supabase ~$100 + Resend Scale ~$120 + hosting ~$50 + Sentry ~$26 |

## 4. Putting it together
- **Infra break-even:** ~**2–3 paying customers** covers the entire fixed platform cost.
- **At $10k MRR (~150 Pro):** $10,000 − variable ~$1,500 − fixed ~$300 = **~$8,200/mo gross profit (~82%)**.
- **At $30k MRR (~430 Pro):** **~$24–25k/mo gross profit**.

| MRR target | ~Pro customers | ~Total monthly cost | ~Gross profit |
|---|---|---|---|
| $1k | ~15 | ~$100 | ~$900 |
| $5k | ~75 | ~$200 | ~$4,800 |
| $10k | ~150 | ~$300 | ~$8,200 |
| $30k | ~430 | ~$700 | ~$24–25k |

## 5. What these numbers exclude (the real costs)
- **Founder time / salary** — the dominant cost at early stage; above is COGS only, not net-net.
- **CAC** — assumes low-cost content/community acquisition; paid ads change the picture entirely.
- **One-off costs** — A2P 10DLC registration (~$50–65), company formation, legal (privacy policy/ToS),
  any paid design/branding, domain + trademark.
- **Support load** — low-tier/founder-deal customers consume disproportionate support time.
- **Power users** — heavy SMS/AI usage costs more; absorbed by spend caps + at-cost overage so margin holds.

**Bottom line:** cheap to run (~$300/mo even at $10k MRR), ~**85% gross margin**, **~$59 profit per Pro
customer/month**. The real constraints are founder time and customer acquisition, not infrastructure.
