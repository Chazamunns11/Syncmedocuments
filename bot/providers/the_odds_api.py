"""The Odds API provider (https://the-odds-api.com).

Free tier gives a monthly quota of requests and covers dozens of bookmakers
across many sports, including Pinnacle (a sharp reference book). Set the API key
in the ODDS_API_KEY environment variable or in config.

Docs: https://the-odds-api.com/liveapi/guides/v4/
"""
from __future__ import annotations

from typing import List, Optional

from ..models import BookOdds, MarketBoard, Outcome
from .base import OddsProvider

API_ROOT = "https://api.the-odds-api.com/v4"


def list_active_sports(api_key: str, timeout: float = 15.0) -> list:
    """Return the sport keys The Odds API currently has live (in-season), as a
    list of (key, title) tuples. Use this to pick valid pinnacle_sports keys —
    seasonal keys (e.g. tennis_atp_aus_open) 404 when the event isn't on."""
    from ..http import get_json
    if not api_key:
        raise ValueError("ODDS_API_KEY required to list sports")
    data, _ = get_json(f"{API_ROOT}/sports", params={"apiKey": api_key},
                       timeout=timeout)
    out = []
    for s in data or []:
        if s.get("active") and not s.get("has_outrights", False):
            out.append((s.get("key"), s.get("title")))
    return out


class TheOddsAPIProvider(OddsProvider):
    name = "the_odds_api"

    def __init__(
        self,
        api_key: str,
        regions: str = "uk,eu",
        odds_format: str = "decimal",
        bookmakers: Optional[List[str]] = None,
        timeout: float = 15.0,
    ):
        if not api_key:
            raise ValueError("The Odds API requires an api_key (ODDS_API_KEY)")
        self.api_key = api_key
        self.regions = regions
        self.odds_format = odds_format
        self.bookmakers = bookmakers
        self.timeout = timeout

    def fetch(self, sport_key: str, markets: List[str]) -> List[MarketBoard]:
        import logging

        from ..http import get_json

        params = {
            "apiKey": self.api_key,
            "markets": ",".join(markets),
            "oddsFormat": self.odds_format,
            "dateFormat": "iso",
        }
        if self.bookmakers:
            params["bookmakers"] = ",".join(self.bookmakers)
        else:
            params["regions"] = self.regions

        url = f"{API_ROOT}/sports/{sport_key}/odds"
        data, headers = get_json(url, params=params, timeout=self.timeout)
        remaining = headers.get("x-requests-remaining")
        if remaining is not None:
            logging.getLogger("value_bot").info(
                "Odds API quota remaining: %s", remaining)
        return self._parse(data, sport_key, markets)

    @staticmethod
    def _parse(data, sport_key: str, markets: List[str]) -> List[MarketBoard]:
        boards: List[MarketBoard] = []
        for event in data:
            event_id = event.get("id", "")
            home = event.get("home_team", "")
            away = event.get("away_team", "")
            commence = event.get("commence_time", "")
            # Group each book's markets so we can build one board per market.
            for market_key in markets:
                books: List[BookOdds] = []
                for bm in event.get("bookmakers", []):
                    for mk in bm.get("markets", []):
                        if mk.get("key") != market_key:
                            continue
                        outcomes = [
                            Outcome(
                                name=o.get("name", ""),
                                price=float(o.get("price", 0) or 0),
                                point=o.get("point"),
                            )
                            for o in mk.get("outcomes", [])
                            if o.get("price")
                        ]
                        if outcomes:
                            books.append(
                                BookOdds(
                                    bookmaker=bm.get("key", bm.get("title", "?")),
                                    market=market_key,
                                    outcomes=outcomes,
                                    last_update=mk.get("last_update"),
                                )
                            )
                if books:
                    boards.append(
                        MarketBoard(
                            event_id=event_id,
                            sport_key=sport_key,
                            commence_time=commence,
                            home_team=home,
                            away_team=away,
                            market=market_key,
                            books=books,
                        )
                    )
        return boards
