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

Matching is alias-aware and STRICT: it requires both teams to match well in a
consistent home/away orientation, and rejects ambiguous matches (where a second
Pinnacle event is almost as good a fit) — because betting the wrong game is the
worst failure mode for real money. Tune ``min_team_score``, ``ambiguity_margin``
and ``start_window_minutes``.
"""
from __future__ import annotations

import datetime as dt
import logging
from typing import Dict, List, Optional, Tuple

from .aliases import normalize, similarity  # noqa: F401 (re-exported)
from .models import BookOdds, FairLine, MarketBoard, Outcome, VenueQuote

log = logging.getLogger("value_bot.matcher")


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
    def __init__(self, min_team_score: float = 0.80,
                 start_window_minutes: int = 90, ambiguity_margin: float = 0.08):
        self.min_team_score = min_team_score
        self.start_window_minutes = start_window_minutes
        # Reject a match if a second candidate event scores within this margin of
        # the best — i.e. the match is ambiguous and could be the wrong game.
        self.ambiguity_margin = ambiguity_margin

    def _event_score(self, fl: FairLine, quotes: List[VenueQuote]) -> float:
        q = quotes[0]
        if not _within_window(fl.commence_time, q.commence_time, self.start_window_minutes):
            return 0.0
        # Require BOTH teams to match in a consistent orientation (teams may be
        # listed home/away in either order across sources).
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
            # Rank candidate Pinnacle lines for this Betfair market.
            scored: List[Tuple[float, FairLine]] = sorted(
                ((self._event_score(fl, mkt_quotes), fl) for fl in fair_lines),
                key=lambda t: t[0], reverse=True)
            if not scored or scored[0][0] < self.min_team_score:
                continue
            best_score, best_fl = scored[0]
            # Ambiguity guard: if the runner-up is almost as good a fit, we can't
            # be sure which game this is — skip rather than risk the wrong bet.
            if len(scored) > 1 and scored[1][0] >= best_score - self.ambiguity_margin \
                    and scored[1][1].event_key != best_fl.event_key:
                log.warning("ambiguous match for %s (%.2f vs %.2f) - skipping",
                            mkt_quotes[0].event_name, best_score, scored[1][0])
                continue

            pinnacle_outcomes = [
                Outcome(name=sel, price=1.0 / p)
                for sel, p in best_fl.probs.items() if p > 0
            ]
            betfair_outcomes = []
            used_selections = set()
            collision = False
            for q in mkt_quotes:
                sel = self._align_runner(q.runner_name, best_fl)
                if sel is None:
                    continue
                # Two runners aligning to the SAME selection means we can't tell
                # them apart -> would bet the wrong runner. Reject the board.
                if sel in used_selections:
                    collision = True
                    break
                used_selections.add(sel)
                betfair_outcomes.append(
                    Outcome(name=sel, price=q.price, selection_id=q.selection_id,
                            size=q.size)
                )
            if collision:
                log.warning("ambiguous runner alignment for %s — skipping",
                            mkt_quotes[0].event_name)
                continue
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
                        # The truth book is kept for transparency/record; the
                        # detector uses fair_probs directly (so consensus models
                        # that already bias-correct aren't re-de-vigged).
                        BookOdds(best_fl.source, "h2h", pinnacle_outcomes),
                        BookOdds("betfair", "h2h", betfair_outcomes,
                                 market_id=market_id),
                    ],
                    fair_probs=dict(best_fl.probs),
                    fair_source=best_fl.source,
                    overround=best_fl.overround,
                )
            )
        return boards
