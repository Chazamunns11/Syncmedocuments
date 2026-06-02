"""Feed-freshness measurement — *prove* a truth feed is real-time, don't assume.

A resold Pinnacle feed only earns the word "real-time" if its lines are actually
fresh. This computes the age of each FairLine (now - last_update) so you can see,
during a dry-run, how stale the feed really is — the single most important thing
to verify before trusting a third-party odds source for a latency-sensitive edge.
"""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from typing import List, Optional, Sequence

from .models import FairLine


def _parse_iso(ts: Optional[str]) -> Optional[_dt.datetime]:
    if not ts:
        return None
    try:
        d = _dt.datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=_dt.timezone.utc)
    except ValueError:
        return None


def line_age_seconds(line: FairLine, now: Optional[_dt.datetime] = None) -> Optional[float]:
    """Age of a line in seconds (None if it carries no usable timestamp)."""
    now = now or _dt.datetime.now(_dt.timezone.utc)
    ts = _parse_iso(line.last_update)
    if ts is None:
        return None
    return (now - ts).total_seconds()


@dataclass
class FreshnessReport:
    n: int
    n_timestamped: int
    median_age: Optional[float]
    max_age: Optional[float]
    fresh_enough: bool       # median within the threshold
    threshold: float
    message: str


def assess_freshness(lines: Sequence[FairLine], threshold_seconds: float = 30.0,
                     now: Optional[_dt.datetime] = None) -> FreshnessReport:
    """Summarise how fresh a batch of truth lines is, vs a staleness threshold."""
    ages: List[float] = []
    for ln in lines:
        a = line_age_seconds(ln, now)
        if a is not None:
            ages.append(a)
    n, n_ts = len(lines), len(ages)
    if not ages:
        return FreshnessReport(n, 0, None, None, False, threshold_seconds,
                               "no timestamps on lines — cannot judge real-time freshness")
    ages.sort()
    median = ages[len(ages) // 2]
    mx = ages[-1]
    fresh = median <= threshold_seconds
    verdict = "FRESH" if fresh else "STALE"
    msg = (f"{verdict}: median line age {median:.0f}s, max {mx:.0f}s "
           f"(threshold {threshold_seconds:.0f}s) over {n_ts}/{n} timestamped lines")
    return FreshnessReport(n, n_ts, median, mx, fresh, threshold_seconds, msg)
