"""Multi-book consensus truth models.

Both Kaunitz et al. (2018, ~480k games + real money) and the practitioner write-up
that followed it converge on the same insight: the aggregate of many bookmakers'
odds is a more accurate estimate of true probability than any single model. We
implement two consensus truth models that turn a market full of bookmaker odds
into a fair probability per outcome:

* ``weighted`` — the practitioner method: de-vig EACH book with the Power Method,
  then take a weighted average of the resulting probabilities (sharp books such
  as Pinnacle weighted higher). Probabilities are normalised to sum to 1. This is
  the default and pairs naturally with placing on Betfair.

* ``kaunitz`` — the paper's method: consensus probability ``p_cons = 1 / mean(odds)``
  per outcome across >= ``min_books`` bookmakers, minus an outcome-specific bias
  term alpha (home/draw/away). Bet when the available price exceeds
  ``1 / (p_cons - alpha)``. Per-outcome and deliberately NOT re-normalised.

Both return :class:`FairLine` objects (with ``overround`` carrying the underlying
booksum as a market-quality signal), consumed identically to Pinnacle lines.
"""
from __future__ import annotations

import datetime as _dt
import math
import statistics
from typing import Dict, List, Optional

from .aliases import similarity
from .devig import booksum, devig
from .models import FairLine, MarketBoard


def _recency_weight(last_update: Optional[str], halflife: float) -> float:
    """Multiplier in (0,1] that decays with the age of a quote. Fresher quotes
    near kickoff (when the line is sharpest) get more weight. halflife<=0 -> 1."""
    if halflife <= 0 or not last_update:
        return 1.0
    try:
        ts = _dt.datetime.fromisoformat(last_update.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=_dt.timezone.utc)
    except (ValueError, TypeError):
        return 1.0
    age = (_dt.datetime.now(_dt.timezone.utc) - ts).total_seconds()
    if age <= 0:
        return 1.0
    return 0.5 ** (age / halflife)

# Kaunitz et al. regression intercepts (bias correction) per outcome.
PAPER_ALPHA = {"home": 0.034, "draw": 0.057, "away": 0.037}


def _role(selection: str, home: str, away: str) -> str:
    """Map a selection name to home/draw/away robustly (tolerant of case,
    whitespace and aliases), so the Kaunitz bias term is applied to the right
    side even when names differ slightly across sources."""
    if selection.lower().strip() in {"draw", "the draw", "tie"}:
        return "draw"
    return "away" if similarity(selection, away) > similarity(selection, home) else "home"


def _weighted_line(board: MarketBoard, book_weights: Dict[str, float],
                   devig_method: str, min_books: int,
                   recency_halflife: float = 0.0) -> Optional[FairLine]:
    selections = board.selections()
    acc = {s: 0.0 for s in selections}
    wsum = 0.0
    overrounds: List[float] = []
    used = 0
    for book in board.books:
        odds = [book.price_for(s) for s in selections]
        if any(o is None for o in odds):
            continue
        try:
            probs = devig(odds, method=devig_method)
        except ValueError:
            continue
        w = book_weights.get(book.bookmaker.lower(), book_weights.get("_default", 1.0))
        w *= _recency_weight(book.last_update, recency_halflife)
        if w <= 0:
            continue
        used += 1
        wsum += w
        overrounds.append(booksum(odds))
        for s, p in zip(selections, probs):
            acc[s] += w * p
    if used < min_books or wsum <= 0:
        return None
    probs = {s: v / wsum for s, v in acc.items()}
    total = sum(probs.values())
    if total <= 0:
        return None
    probs = {s: p / total for s, p in probs.items()}
    return FairLine(
        event_key=board.event_id, sport_key=board.sport_key,
        commence_time=board.commence_time, home_team=board.home_team,
        away_team=board.away_team, market=board.market, probs=probs,
        source="weighted", overround=statistics.mean(overrounds),
    )


def _kaunitz_line(board: MarketBoard, alpha: Dict[str, float],
                  min_books: int) -> Optional[FairLine]:
    selections = board.selections()
    probs: Dict[str, float] = {}
    for s in selections:
        odds = [b.price_for(s) for b in board.books]
        odds = [o for o in odds if o and o > 1.0]
        if len(odds) < min_books:
            continue
        p_cons = 1.0 / statistics.mean(odds)            # Eq. 1
        a = alpha.get(_role(s, board.home_team, board.away_team), 0.0)
        p_real = p_cons - a                             # Eq. 4
        if p_real > 0:
            probs[s] = p_real
    if not probs:
        return None
    # Mean booksum across books that quote the full market (quality signal).
    overrounds = []
    for b in board.books:
        odds = [b.price_for(s) for s in selections]
        if all(o for o in odds):
            overrounds.append(booksum(odds))
    return FairLine(
        event_key=board.event_id, sport_key=board.sport_key,
        commence_time=board.commence_time, home_team=board.home_team,
        away_team=board.away_team, market=board.market, probs=probs,
        source="consensus",
        overround=statistics.mean(overrounds) if overrounds else None,
    )


def consensus_lines_from_boards(
    boards: List[MarketBoard],
    method: str = "weighted",
    book_weights: Optional[Dict[str, float]] = None,
    devig_method: str = "power",
    alpha: Optional[Dict[str, float]] = None,
    min_books: int = 3,
    recency_halflife: float = 0.0,
) -> List[FairLine]:
    """Build consensus FairLines from multi-book market boards."""
    book_weights = {k.lower(): v for k, v in (book_weights or {}).items()}
    alpha = alpha or {"home": 0.05, "draw": 0.05, "away": 0.05}
    lines: List[FairLine] = []
    for board in boards:
        if method == "weighted":
            fl = _weighted_line(board, book_weights, devig_method, min_books,
                                recency_halflife)
        elif method == "kaunitz":
            fl = _kaunitz_line(board, alpha, min_books)
        else:
            raise ValueError(f"unknown consensus method {method!r}")
        if fl:
            lines.append(fl)
    return lines


def consensus_lines_via_odds_api(
    api_key: str, sport_key: str, regions: str = "uk,eu",
    method: str = "weighted", book_weights: Optional[Dict[str, float]] = None,
    devig_method: str = "power", alpha: Optional[Dict[str, float]] = None,
    min_books: int = 3, recency_halflife: float = 0.0,
) -> List[FairLine]:
    """Fetch the full bookmaker market via The Odds API and build consensus lines."""
    from .providers.the_odds_api import TheOddsAPIProvider

    boards = TheOddsAPIProvider(api_key=api_key, regions=regions).fetch(
        sport_key, ["h2h"])
    return consensus_lines_from_boards(
        boards, method=method, book_weights=book_weights,
        devig_method=devig_method, alpha=alpha, min_books=min_books,
        recency_halflife=recency_halflife)
