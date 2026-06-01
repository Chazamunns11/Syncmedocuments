"""Match Pinnacle (truth) events to Betfair (venue) events and align selections.

The two sources don't share ids, so events are paired by team-name similarity and
start time, and each Betfair runner is aligned to the Pinnacle selection name it
refers to. The output is a list of :class:`MarketBoard`, each containing exactly
two books:

  * ``pinnacle`` — reconstructed from the fair probabilities (odds = 1/prob),
  * ``betfair``  — gross back prices, carrying market_id + selection_id so the
    bet can be placed directly.

Feeding these boards to ``ValueDetector(reference_books=["pinnacle"],
commission=...)`` then yields +EV Betfair bets, reusing all the tested value
logic.

Name matching is inherently fuzzy. Tune ``min_team_score`` and
``start_window_minutes``, and review matches (especially before live placement).
"""
from __future__ import annotations

import datetime as dt
import difflib
import re
from typing import Dict, List, Optional

from .models import BookOdds, FairLine, MarketBoard, Outcome, VenueQuote

_NOISE = re.compile(r"\b(fc|cf|afc|sc|club|the|city|united|utd|town)\b")
_NONWORD = re.compile(r"[^a-z0-9 ]")


def normalize(name: str) -> str:
    s = name.lower().strip()
    s = _NONWORD.sub(" ", s)
    s = _NOISE.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, normalize(a), normalize(b)).ratio()


def _parse_time(s: str) -> Optional[dt.datetime]:
    if not s:
        return None
    try:
        return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _within_window(a: str, b: str, minutes: int) -> bool:
    ta, tb = _parse_time(a), _parse_time(b)
    if ta is None or tb is None:
        return True  # can't compare -> don't exclude on time
    return abs((ta - tb).total_seconds()) <= minutes * 60


class EventMatcher:
    def __init__(self, min_team_score: float = 0.6, start_window_minutes: int = 90):
        self.min_team_score = min_team_score
        self.start_window_minutes = start_window_minutes

    def _event_score(self, fl: FairLine, quotes: List[VenueQuote]) -> float:
        q = quotes[0]
        if not _within_window(fl.commence_time, q.commence_time, self.start_window_minutes):
            return 0.0
        # Score both home/away orderings; teams may be swapped across sources.
        straight = min(similarity(fl.home_team, q.home_team),
                       similarity(fl.away_team, q.away_team))
        swapped = min(similarity(fl.home_team, q.away_team),
                      similarity(fl.away_team, q.home_team))
        return max(straight, swapped)

    def _align_runner(self, runner_name: str, fl: FairLine) -> Optional[str]:
        """Map a Betfair runner name to the matching Pinnacle selection name."""
        best_name, best_score = None, 0.0
        for sel in fl.probs:
            if sel.lower() in {"draw", "the draw"} and \
                    runner_name.lower() in {"draw", "the draw"}:
                return sel
            score = similarity(sel, runner_name)
            if score > best_score:
                best_name, best_score = sel, score
        return best_name if best_score >= self.min_team_score else None

    def build_boards(
        self, fair_lines: List[FairLine], quotes: List[VenueQuote]
    ) -> List[MarketBoard]:
        # Group venue quotes by market (event).
        by_market: Dict[str, List[VenueQuote]] = {}
        for q in quotes:
            by_market.setdefault(q.market_id, []).append(q)

        boards: List[MarketBoard] = []
        for market_id, mkt_quotes in by_market.items():
            # Find the best-matching Pinnacle fair line for this Betfair market.
            best_fl, best_score = None, 0.0
            for fl in fair_lines:
                score = self._event_score(fl, mkt_quotes)
                if score > best_score:
                    best_fl, best_score = fl, score
            if best_fl is None or best_score < self.min_team_score:
                continue

            pinnacle_outcomes = [
                Outcome(name=sel, price=1.0 / p)
                for sel, p in best_fl.probs.items() if p > 0
            ]
            betfair_outcomes = []
            for q in mkt_quotes:
                sel = self._align_runner(q.runner_name, best_fl)
                if sel is None:
                    continue
                betfair_outcomes.append(
                    Outcome(name=sel, price=q.price, selection_id=q.selection_id,
                            size=q.size)
                )
            if not betfair_outcomes:
                continue

            boards.append(
                MarketBoard(
                    event_id=best_fl.event_key,
                    sport_key=best_fl.sport_key,
                    commence_time=best_fl.commence_time,
                    home_team=best_fl.home_team,
                    away_team=best_fl.away_team,
                    market="h2h",
                    books=[
                        BookOdds("pinnacle", "h2h", pinnacle_outcomes),
                        BookOdds("betfair", "h2h", betfair_outcomes,
                                 market_id=market_id),
                    ],
                )
            )
        return boards
