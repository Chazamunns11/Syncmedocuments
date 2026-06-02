"""Turn a log of per-bet CLV into an honest go/no-go verdict.

Average CLV over a handful of bets is noise. This applies the standard test for
"is the mean genuinely above zero?" — a confidence interval on the mean CLV —
and tells you either GO (edge is real), NO-GO (it isn't), or how many more bets
you need before the question can be answered. Pure stdlib, offline, testable.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Sequence

Z95 = 1.96  # two-sided 95% normal critical value (conservative for real money)


@dataclass
class CLVVerdict:
    n: int
    mean: float          # mean CLV (fraction, e.g. 0.018 = +1.8%)
    sd: float            # sample standard deviation
    se: float            # standard error of the mean
    ci_low: float        # 95% CI lower bound on the mean
    ci_high: float       # 95% CI upper bound on the mean
    beat_rate: float     # fraction of bets with CLV > 0
    min_n: int
    verdict: str         # "GO" | "NO-GO" | "COLLECT"
    bets_needed: int     # extra bets to resolve, if positive-but-not-yet-significant
    message: str


def assess_clv(samples: Sequence[float], min_n: int = 100) -> CLVVerdict:
    """Assess a list of per-bet CLV values (clv_market preferred)."""
    xs: List[float] = [float(x) for x in samples if x is not None]
    n = len(xs)
    if n == 0:
        return CLVVerdict(0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, min_n, "COLLECT", min_n,
                          "No CLV captured yet — let the dry-run place and settle bets.")
    mean = sum(xs) / n
    beat_rate = sum(1 for x in xs if x > 0) / n
    if n < 2:
        return CLVVerdict(n, mean, 0.0, 0.0, mean, mean, beat_rate, min_n,
                          "COLLECT", max(0, min_n - n),
                          f"Only {n} bet — far too few. Need ~{min_n}.")
    var = sum((x - mean) ** 2 for x in xs) / (n - 1)
    sd = math.sqrt(var)
    se = sd / math.sqrt(n)
    ci_low, ci_high = mean - Z95 * se, mean + Z95 * se

    # Extra bets to make the CI exclude zero, if the effect/noise persist.
    bets_needed = 0
    if mean > 0 and sd > 0:
        n_star = (Z95 * sd / mean) ** 2
        bets_needed = max(0, math.ceil(n_star) - n)

    if n < min_n:
        verdict = "COLLECT"
        msg = (f"{n}/{min_n} bets — too few to trust CLV yet. "
               f"Keep the dry-run running.")
    elif mean <= 0:
        verdict = "NO-GO"
        msg = ("Mean CLV is not positive — no demonstrable edge. "
               "Do NOT stake real money on this config.")
    elif ci_low > 0:
        verdict = "GO"
        msg = ("CLV is significantly positive (95% CI excludes zero). "
               "The edge looks real — proceed to tiny real stakes.")
    else:
        verdict = "COLLECT"
        msg = (f"CLV is positive but not yet significant. "
               f"~{bets_needed} more bets needed to confirm (if it holds).")
    return CLVVerdict(n, mean, sd, se, ci_low, ci_high, beat_rate, min_n,
                      verdict, bets_needed, msg)


def format_verdict(title: str, v: CLVVerdict) -> str:
    pct = lambda x: f"{x * 100:+.2f}%"
    badge = {"GO": "✅ GO", "NO-GO": "🛑 NO-GO", "COLLECT": "⏳ KEEP COLLECTING"}[v.verdict]
    lines = [
        f"{title}: {badge}",
        f"   bets:        {v.n}  (target ≥ {v.min_n})",
        f"   mean CLV:    {pct(v.mean)}   beat-rate {v.beat_rate * 100:.0f}%",
        f"   95% CI:      [{pct(v.ci_low)}, {pct(v.ci_high)}]",
        f"   {v.message}",
    ]
    return "\n".join(lines)
