"""De-vigging: turn a bookmaker's odds into fair win probabilities.

A bookmaker's decimal odds embed a margin (the "vig" / "overround"): the implied
probabilities across all outcomes sum to more than 1. To estimate the *true*
probability of an outcome we strip that margin out.

Three standard methods are provided:

* ``multiplicative`` (a.k.a. proportional / normalisation) — divide each implied
  probability by the booksum. Simple and unbiased if the margin is applied
  proportionally. This is the sensible default.
* ``additive`` — subtract an equal share of the margin from each outcome.
* ``shin`` — Shin's (1992/93) model, which attributes the margin to the presence
  of insider traders and shifts probability away from favourites toward
  longshots. Generally the most accurate for two-way and lopsided markets.

All functions take a list of decimal odds and return a list of fair
probabilities that sum to 1.
"""
from __future__ import annotations

import math
from typing import List

Method = str
SUPPORTED_METHODS = ("multiplicative", "additive", "shin")


def _validate(odds: List[float]) -> None:
    if len(odds) < 2:
        raise ValueError("need at least two outcomes to de-vig a market")
    if any(o <= 1.0 for o in odds):
        raise ValueError(f"decimal odds must be > 1.0, got {odds}")


def implied(odds: List[float]) -> List[float]:
    """Raw implied probabilities (1/odds), not normalised."""
    return [1.0 / o for o in odds]


def booksum(odds: List[float]) -> float:
    """Sum of raw implied probabilities. > 1.0 means there is a margin."""
    return sum(implied(odds))


def multiplicative(odds: List[float]) -> List[float]:
    _validate(odds)
    q = implied(odds)
    total = sum(q)
    return [x / total for x in q]


def additive(odds: List[float]) -> List[float]:
    _validate(odds)
    q = implied(odds)
    n = len(q)
    margin = sum(q) - 1.0
    fair = [x - margin / n for x in q]
    # Equal-margin removal can push a heavy favourite below 0; clamp + renorm.
    if any(p <= 0 for p in fair):
        return multiplicative(odds)
    total = sum(fair)
    return [p / total for p in fair]


def shin(odds: List[float], max_iter: int = 100, tol: float = 1e-12) -> List[float]:
    """Shin's method. Solves for the insider-trading proportion ``z`` such that
    the recovered probabilities sum to 1, via bisection on z in [0, 1)."""
    _validate(odds)
    q = implied(odds)
    B = sum(q)
    if B <= 1.0:  # no margin to remove
        return multiplicative(odds)

    def probs_for(z: float) -> List[float]:
        out = []
        for qi in q:
            val = math.sqrt(z * z + 4.0 * (1.0 - z) * (qi * qi) / B)
            out.append((val - z) / (2.0 * (1.0 - z)))
        return out

    lo, hi = 0.0, 0.999999
    # sum(probs_for(z)) is monotone decreasing in z; find the root of sum-1.
    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        s = sum(probs_for(mid))
        if abs(s - 1.0) < tol:
            break
        if s > 1.0:
            lo = mid
        else:
            hi = mid
    z = 0.5 * (lo + hi)
    p = probs_for(z)
    total = sum(p)
    return [x / total for x in p]


def devig(odds: List[float], method: Method = "multiplicative") -> List[float]:
    """Dispatch to the requested de-vig method."""
    if method == "multiplicative":
        return multiplicative(odds)
    if method == "additive":
        return additive(odds)
    if method == "shin":
        return shin(odds)
    raise ValueError(
        f"unknown de-vig method {method!r}; choose one of {SUPPORTED_METHODS}"
    )
