# Odds sources & APIs — what's actually available (verified 2026)

Two things to source: a **sharp "truth" signal** (to find value + detect line
drops) and a **venue** (where to place — must not ban winners). Below is the
current, verified landscape, with what's automatable.

## Sharp / truth signal (find value, detect drops)

| Source | API? | Latency | Pinnacle? | Cost | Verdict for a fully-automated bot |
|---|---|---|---|---|---|
| **Pinnacle direct** (api.pinnacle.com) | ❌ **DEAD** | — | — | — | Public API shut **Jul 2025**. Not an option. |
| **The Odds API** | ✅ REST | secs (top tier) only | ❌ **No Pinnacle** (~40 soft books) | credits = markets×regions; free 500 | Good for **soft-book weighted consensus** truth. No Pinnacle. |
| **RapidAPI "Pinnacle Odds"** (pinnacle-odds) | ✅ REST | "no delay" | ✅ raw Pinnacle odds | RapidAPI tiers | **Built in** → `pinnacle_source: rapidapi`. Best for full control: we get raw odds, detect drops + CLV ourselves. |
| **OddAlerts API** | ✅ REST + Telegram | real-time | ✅ de-vigged Pinnacle | 48h free trial, then sub | Most **turnkey** automatable: `/value/you/{id}` returns filtered value bets (prob, odds, value%); real-time Pinnacle dropping-odds. Built for bots. |
| **Pinnacle Odds Dropper (POD)** | ❌ push/sound only | real-time | ✅ | $39 / $69 mo | Great *signal*, but **not cleanly automatable** (no API/webhook; alerts to a human). Manual/semi-auto + CLV tracking. |
| **pinndrops / SportsGameOdds / SportsFirst** | varies | real-time | ✅ resellers | sub | Alternative Pinnacle resellers; check each for a REST/Telegram feed. |

**Bottom line on truth:** for *full automation*, use **`rapidapi`** (raw Pinnacle,
we own the logic — already wired) or **OddAlerts API** (turnkey value bets). Fall
back to **`truth_model: weighted`** (soft-book consensus via The Odds API) if you
don't want a Pinnacle subscription — it works with just an Odds API key.

## Venue (where to place — none of these ban winners)

| Venue | API | Commission | Premium charge | Notes |
|---|---|---|---|---|
| **Betfair Exchange** | ✅ real-time streaming, free data (app key) | 2–5% | ⚠️ up to 60% | Deepest liquidity. **Integrated.** |
| **Smarkets** | ✅ HTTP API (official Python SDK) | **1%** (Pro/API tier), 1 bet/s | ❌ none | Lowest commission. Streaming is market-makers only. **Best net yield.** |
| **Matchbook** | ✅ REST (standard login) | 1.5% (0.75% maker); UK 2% net | ❌ none | "Matchbook Zero" 0% on select events. |
| **Betdaq** | ✅ API | ~2% | ❌ none | Thinner liquidity. |

**Bottom line on venue:** **Smarkets** (1%, no premium charge, real API) is the
highest net-yield automatable venue — commission is the biggest lever now that
matched betting is gone.

## Recommended fully-automated stack

```
TRUTH:  pinnacle_source: rapidapi   (raw real-time Pinnacle → our drop/CLV logic)
        # or OddAlerts API; or truth_model: weighted (Odds API consensus, no Pinnacle sub)
VENUE:  Smarkets (1%, no premium charge)   ← build the executor; Betfair already done
LOGIC:  line-move tracker (detect the drop) → CLV-first selection → paper→validate→live
```

The bot already implements the detection (line-move tracker), CLV-first ranking,
and CLV validation. The remaining live integration is the **Smarkets executor**.
See `DRYRUN.md` to validate risk-free before any money goes in.
