"""Shared Betfair Exchange session.

One client serves both roles:
  * **price source** — pull current best back prices (``list_match_odds``), so we
    can find value on the exchange, and
  * **executor** — place a back bet by market_id/selection_id.

Because both come from the same market catalogue, a runner we price is the exact
runner we place on — no fuzzy matching on the placement side.

``betfairlightweight`` is imported lazily, so importing this module never
requires the dependency. Sign-up + Application Key: https://developer.betfair.com
"""
from __future__ import annotations

from typing import Dict, List, Optional

from .models import VenueQuote

# Betfair event type ids for the common sports.
EVENT_TYPE_IDS = {
    "soccer": "1",
    "tennis": "2",
    "golf": "3",
    "cricket": "4",
    "rugby_union": "5",
    "boxing": "6",
    "horse_racing": "7",
    "basketball": "7522",
    "american_football": "6423",
    "baseball": "7511",
    "ice_hockey": "7524",
}

# Betfair price ladder (decimal): (upper_bound_exclusive, tick_size).
_LADDER = [
    (2.0, 0.01), (3.0, 0.02), (4.0, 0.05), (6.0, 0.1), (10.0, 0.2),
    (20.0, 0.5), (30.0, 1.0), (50.0, 2.0), (100.0, 5.0), (1000.0, 10.0),
]


def nearest_tick(price: float) -> float:
    """Round a decimal price to the nearest valid Betfair tick (1.01–1000)."""
    if price <= 1.01:
        return 1.01
    if price >= 1000:
        return 1000.0
    lower = 1.01
    for upper, tick in _LADDER:
        if price < upper:
            steps = round((price - lower) / tick)
            return round(lower + steps * tick, 2)
        lower = upper
    return round(price, 2)


class BetfairClient:
    def __init__(
        self,
        username: str,
        password: str,
        app_key: str,
        certs_path: Optional[str] = None,
        locale: str = "en",
    ):
        if not (username and password and app_key):
            raise ValueError("Betfair requires username, password and app_key")
        self.username = username
        self.password = password
        self.app_key = app_key
        self.certs_path = certs_path
        self.locale = locale
        self._client = None

    # -- session -----------------------------------------------------------
    def trading(self):
        if self._client is not None:
            return self._client
        try:
            import betfairlightweight
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "betfairlightweight is not installed. Run "
                "`pip install betfairlightweight` to use Betfair."
            ) from exc
        client = betfairlightweight.APIClient(
            username=self.username,
            password=self.password,
            app_key=self.app_key,
            certs=self.certs_path,
            locale=self.locale,
        )
        if self.certs_path:
            client.login()
        else:
            client.login_interactive()
        self._client = client
        return client

    def close(self) -> None:
        if self._client is not None:
            try:
                self._client.logout()
            except Exception:
                pass
            self._client = None

    # -- prices ------------------------------------------------------------
    def list_match_odds(
        self,
        event_type_id: str,
        competition_ids: Optional[List[str]] = None,
        max_markets: int = 50,
        market_start_within_hours: Optional[int] = None,
    ) -> List[VenueQuote]:
        """Return best-available back quotes for MATCH_ODDS markets."""
        import datetime as dt

        from betfairlightweight import filters

        client = self.trading()
        mf_kwargs = dict(
            event_type_ids=[event_type_id],
            market_type_codes=["MATCH_ODDS"],
        )
        if competition_ids:
            mf_kwargs["competition_ids"] = competition_ids
        if market_start_within_hours:
            now = dt.datetime.utcnow()
            end = now + dt.timedelta(hours=market_start_within_hours)
            mf_kwargs["market_start_time"] = {
                "from": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "to": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        market_filter = filters.market_filter(**mf_kwargs)

        catalogues = client.betting.list_market_catalogue(
            filter=market_filter,
            market_projection=["RUNNER_DESCRIPTION", "EVENT", "MARKET_START_TIME"],
            max_results=max_markets,
            sort="MAXIMUM_TRADED",
        )
        if not catalogues:
            return []

        # selection_id -> runner_name, and market_id -> event meta
        runner_names: Dict[str, Dict[str, str]] = {}
        market_meta: Dict[str, dict] = {}
        for cat in catalogues:
            names = {str(r.selection_id): r.runner_name for r in cat.runners}
            runner_names[cat.market_id] = names
            home, away = _split_event_name(cat.event.name)
            market_meta[cat.market_id] = {
                "event_name": cat.event.name,
                "home": home,
                "away": away,
                "start": getattr(cat, "market_start_time", None),
            }

        market_ids = [c.market_id for c in catalogues]
        books = client.betting.list_market_book(
            market_ids=market_ids,
            price_projection=filters.price_projection(
                price_data=filters.price_data(ex_best_offers=True)
            ),
        )

        quotes: List[VenueQuote] = []
        for book in books:
            meta = market_meta.get(book.market_id, {})
            names = runner_names.get(book.market_id, {})
            for runner in book.runners:
                back = runner.ex.available_to_back if runner.ex else []
                if not back:
                    continue
                best = back[0]
                sid = str(runner.selection_id)
                quotes.append(
                    VenueQuote(
                        venue="betfair",
                        market_id=book.market_id,
                        selection_id=sid,
                        runner_name=names.get(sid, sid),
                        price=float(best.price),
                        size=float(best.size),
                        event_name=meta.get("event_name", ""),
                        home_team=meta.get("home", ""),
                        away_team=meta.get("away", ""),
                        commence_time=str(meta.get("start", "")),
                        market="h2h",
                    )
                )
        return quotes

    # -- placement ---------------------------------------------------------
    def place_back(
        self,
        market_id: str,
        selection_id: str,
        price: float,
        size: float,
        persistence: str = "LAPSE",
    ):
        """Place a single BACK limit order. Returns the place report."""
        from betfairlightweight import filters

        client = self.trading()
        order = filters.limit_order(
            size=round(size, 2),
            price=nearest_tick(price),
            persistence_type=persistence,
        )
        instruction = filters.place_instruction(
            order_type="LIMIT",
            selection_id=int(selection_id),
            side="BACK",
            limit_order=order,
        )
        return client.betting.place_orders(
            market_id=market_id, instructions=[instruction]
        )


def _split_event_name(name: str):
    """Betfair event names are usually 'Home v Away'. Return (home, away)."""
    for sep in (" v ", " vs ", " @ ", " - "):
        if sep in name:
            a, b = name.split(sep, 1)
            return a.strip(), b.strip()
    return name.strip(), ""
