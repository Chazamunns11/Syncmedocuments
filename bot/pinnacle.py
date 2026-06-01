"""Pinnacle as the source of truth.

Pinnacle is the sharpest mainstream book: it prices close to true probability and
welcomes winners, so its de-vigged line is the best cheap estimate of a fair
price. We use it ONLY to value bets — the bets themselves go on Betfair.

Two ways to obtain Pinnacle's prices, chosen by ``pinnacle_source``:

* ``"direct"`` — Pinnacle's own API (https://api.pinnacle.com), HTTP Basic auth
  with your Pinnacle account. NOTE: Pinnacle left the UK market, so UK customers
  generally cannot open an account / get API access. Use this only if you have a
  funded Pinnacle account in a supported region.
* ``"the_odds_api"`` — pull Pinnacle's line via The Odds API (it aggregates
  Pinnacle as bookmaker key ``pinnacle``). Works from anywhere with an API key.
  This is the practical default for UK users.
* ``"sample"`` — offline demo data, no network/credentials.

All paths return a list of :class:`FairLine` (de-vigged probabilities per
selection) for h2h / moneyline markets.
"""
from __future__ import annotations

from typing import List, Optional

from .devig import devig
from .models import FairLine

PINNACLE_API_ROOT = "https://api.pinnacle.com"

# Pinnacle sportId for the common sports (v2 /sports lists the full set).
PINNACLE_SPORT_IDS = {
    "soccer": 29,
    "tennis": 33,
    "basketball": 4,
    "baseball": 3,
    "hockey": 19,
    "football": 15,  # American football
}


def _fair_line_from_three_way(
    event_key, sport_key, commence, home, away, home_odds, draw_odds,
    away_odds, method,
) -> Optional[FairLine]:
    names = [home, "Draw", away]
    odds = [home_odds, draw_odds, away_odds]
    pairs = [(n, o) for n, o in zip(names, odds) if o and o > 1.0]
    if len(pairs) < 2:
        return None
    try:
        probs = devig([o for _, o in pairs], method=method)
    except ValueError:
        return None
    return FairLine(
        event_key=str(event_key), sport_key=sport_key, commence_time=str(commence),
        home_team=home, away_team=away, market="h2h",
        probs={n: p for (n, _), p in zip(pairs, probs)}, source="pinnacle",
    )


class PinnacleClient:
    """Direct Pinnacle API client (HTTP Basic auth)."""

    def __init__(self, username: str, password: str, timeout: float = 15.0):
        if not (username and password):
            raise ValueError("Pinnacle direct API needs PINNACLE_USERNAME/PASSWORD")
        self.username = username
        self.password = password
        self.timeout = timeout

    def fair_lines(self, sport: str, devig_method: str = "multiplicative") -> List[FairLine]:
        import requests

        sport_id = PINNACLE_SPORT_IDS.get(sport)
        if sport_id is None:
            raise ValueError(f"unknown Pinnacle sport {sport!r}")
        auth = (self.username, self.password)

        fixtures = requests.get(
            f"{PINNACLE_API_ROOT}/v1/fixtures",
            params={"sportId": sport_id}, auth=auth, timeout=self.timeout,
        )
        fixtures.raise_for_status()
        odds = requests.get(
            f"{PINNACLE_API_ROOT}/v1/odds",
            params={"sportId": sport_id, "oddsFormat": "Decimal"},
            auth=auth, timeout=self.timeout,
        )
        odds.raise_for_status()
        return self._join(fixtures.json(), odds.json(), sport, devig_method)

    @staticmethod
    def _join(fixtures_json, odds_json, sport, method) -> List[FairLine]:
        # event id -> (home, away, starts)
        meta = {}
        for league in fixtures_json.get("league", []):
            for ev in league.get("events", []):
                meta[ev.get("id")] = (
                    ev.get("home", ""), ev.get("away", ""), ev.get("starts", ""),
                )
        lines: List[FairLine] = []
        for league in odds_json.get("leagues", []):
            for ev in league.get("events", []):
                home, away, starts = meta.get(ev.get("id"), ("", "", ""))
                if not home:
                    continue
                for period in ev.get("periods", []):
                    if period.get("number") != 0:  # full match only
                        continue
                    ml = period.get("moneyline")
                    if not ml:
                        continue
                    fl = _fair_line_from_three_way(
                        ev.get("id"), sport, starts, home, away,
                        ml.get("home"), ml.get("draw"), ml.get("away"), method,
                    )
                    if fl:
                        lines.append(fl)
        return lines


def pinnacle_lines_via_odds_api(
    api_key: str, sport_key: str, regions: str = "uk,eu",
    devig_method: str = "multiplicative",
) -> List[FairLine]:
    """Fetch Pinnacle's line through The Odds API and de-vig it."""
    from .providers.the_odds_api import TheOddsAPIProvider

    provider = TheOddsAPIProvider(
        api_key=api_key, regions=regions, bookmakers=["pinnacle"],
    )
    boards = provider.fetch(sport_key, ["h2h"])
    lines: List[FairLine] = []
    for board in boards:
        pin = next((b for b in board.books if b.bookmaker.lower() == "pinnacle"), None)
        if pin is None:
            continue
        names = [o.name for o in pin.outcomes]
        odds = [o.price for o in pin.outcomes]
        if len(odds) < 2:
            continue
        try:
            probs = devig(odds, method=devig_method)
        except ValueError:
            continue
        lines.append(
            FairLine(
                event_key=board.event_id, sport_key=sport_key,
                commence_time=board.commence_time, home_team=board.home_team,
                away_team=board.away_team, market="h2h",
                probs=dict(zip(names, probs)), source="pinnacle",
                last_update=pin.last_update,
            )
        )
    return lines
