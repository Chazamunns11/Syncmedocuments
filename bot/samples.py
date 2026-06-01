"""Offline sample data for the Pinnacle -> Betfair pipeline.

Lets `python run.py run` (mode=pinnacle_betfair) work end-to-end with no
credentials or network. The Betfair back price on the home side is seeded above
Pinnacle's fair price so a value bet is found even after commission.
"""
from __future__ import annotations

import datetime as _dt
from typing import List

from .devig import devig
from .models import FairLine, VenueQuote


def _soon(seconds: float) -> str:
    """ISO timestamp ``seconds`` from now (UTC), so the offline demo has events
    near kickoff for the continuous watcher to place on."""
    return (_dt.datetime.now(_dt.timezone.utc)
            + _dt.timedelta(seconds=seconds)).isoformat()


# Event 1 starts ~2 minutes out (inside the default place window for `watch`);
# event 2 starts ~2 hours out (well outside it).
_T1 = _soon(120)
_T2 = _soon(7200)


def sample_pinnacle_lines(sport_key: str = "soccer_epl") -> List[FairLine]:
    lines = []
    # Pinnacle 1X2 with a small margin -> fair ~ {Arsenal .50, Draw .27, Chelsea .23}
    names = ["Arsenal", "Draw", "Chelsea"]
    odds = [1.95, 3.60, 4.20]
    probs = devig(odds, "multiplicative")
    lines.append(FairLine(
        event_key="pin_1", sport_key=sport_key,
        commence_time=_T1,
        home_team="Arsenal", away_team="Chelsea", market="h2h",
        probs=dict(zip(names, probs)), source="pinnacle",
    ))
    # An efficient event: Betfair will sit on/under fair -> no value.
    names2 = ["Liverpool", "Draw", "Everton"]
    odds2 = [1.50, 4.20, 7.00]
    probs2 = devig(odds2, "multiplicative")
    lines.append(FairLine(
        event_key="pin_2", sport_key=sport_key,
        commence_time=_T2,
        home_team="Liverpool", away_team="Everton", market="h2h",
        probs=dict(zip(names2, probs2)), source="pinnacle",
    ))
    return lines


def sample_betfair_quotes() -> List[VenueQuote]:
    return [
        # Event 1: Arsenal backable at 2.20 vs Pinnacle fair ~2.00 -> value.
        VenueQuote("betfair", "1.111", "47999", "Arsenal", 2.20, 350.0,
                   "Arsenal v Chelsea", "Arsenal", "Chelsea",
                   _T1, "h2h"),
        VenueQuote("betfair", "1.111", "47998", "Chelsea", 4.10, 120.0,
                   "Arsenal v Chelsea", "Arsenal", "Chelsea",
                   _T1, "h2h"),
        VenueQuote("betfair", "1.111", "58805", "The Draw", 3.55, 200.0,
                   "Arsenal v Chelsea", "Arsenal", "Chelsea",
                   _T1, "h2h"),
        # Event 2: priced at/under fair -> no value after commission.
        VenueQuote("betfair", "1.222", "12345", "Liverpool", 1.49, 500.0,
                   "Liverpool v Everton", "Liverpool", "Everton",
                   _T2, "h2h"),
        VenueQuote("betfair", "1.222", "12346", "Everton", 6.80, 90.0,
                   "Liverpool v Everton", "Liverpool", "Everton",
                   _T2, "h2h"),
    ]
