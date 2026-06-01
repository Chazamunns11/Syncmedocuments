"""Core data models shared across the bot.

These are plain dataclasses with no third-party dependencies so they can be
imported anywhere (providers, detector, executors, store) without pulling in
network libraries.
"""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional


def utcnow_iso() -> str:
    """Timezone-aware UTC timestamp as an ISO-8601 string."""
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


@dataclass
class Outcome:
    """A single selectable result within a market and its decimal odds."""

    name: str
    price: float  # decimal odds, e.g. 2.50
    point: Optional[float] = None  # handicap / total line, if applicable
    # Exchange identifiers, populated when this outcome is a venue (Betfair)
    # runner, so it can be placed without any fuzzy name matching.
    selection_id: Optional[str] = None
    size: Optional[float] = None  # amount available to back at this price


@dataclass
class BookOdds:
    """One bookmaker's prices for one market of one event."""

    bookmaker: str
    market: str  # e.g. "h2h", "spreads", "totals"
    outcomes: List[Outcome]
    last_update: Optional[str] = None
    market_id: Optional[str] = None  # exchange market id, for placement

    def price_for(self, selection: str) -> Optional[float]:
        for o in self.outcomes:
            if o.name == selection:
                return o.price
        return None


@dataclass
class MarketBoard:
    """All bookmakers' prices for a single market of a single event.

    This is the unit the value detector consumes: it has every book's odds for
    the same set of outcomes, so it can build a fair price from a reference book
    and compare every other book against it.
    """

    event_id: str
    sport_key: str
    commence_time: str
    home_team: str
    away_team: str
    market: str
    books: List[BookOdds] = field(default_factory=list)

    def selections(self) -> List[str]:
        """Union of outcome names seen across all books (stable order)."""
        seen: List[str] = []
        for b in self.books:
            for o in b.outcomes:
                if o.name not in seen:
                    seen.append(o.name)
        return seen


@dataclass
class ValueBet:
    """A +EV opportunity identified by the detector."""

    event_id: str
    sport_key: str
    commence_time: str
    matchup: str
    market: str
    selection: str
    bookmaker: str           # where the value price is offered
    price: float             # decimal odds we intend to take
    fair_prob: float         # de-vigged probability of winning
    fair_price: float        # 1 / fair_prob
    edge: float              # price / fair_price - 1  (relative overlay)
    ev: float                # expected profit per 1 unit staked (net of commission)
    kelly_fraction: float    # fraction of bankroll suggested (pre-cap)
    stake: float = 0.0       # actual stake assigned by bankroll manager
    # Exchange / commission detail (populated for venue bets such as Betfair).
    commission: float = 0.0          # commission rate applied to net winnings
    eff_price: Optional[float] = None  # commission-adjusted decimal odds used for EV
    venue_market_id: Optional[str] = None
    venue_selection_id: Optional[str] = None
    available_size: Optional[float] = None  # liquidity available at the venue price
    identified_at: str = field(default_factory=utcnow_iso)

    @property
    def key(self) -> str:
        """Stable de-duplication key for a given opportunity."""
        return f"{self.event_id}|{self.market}|{self.selection}|{self.bookmaker}"

    def to_row(self) -> Dict:
        return asdict(self)


@dataclass
class PlacementResult:
    """Outcome of attempting to place a bet through an executor."""

    bet_key: str
    executor: str             # "paper" | "betfair" | ...
    status: str               # "PLACED" | "MATCHED" | "REJECTED" | "ERROR" | "DRY_RUN"
    requested_price: float
    requested_stake: float
    matched_price: Optional[float] = None
    matched_stake: Optional[float] = None
    external_ref: Optional[str] = None   # bookmaker/exchange bet id
    message: str = ""
    placed_at: str = field(default_factory=utcnow_iso)

    @property
    def ok(self) -> bool:
        return self.status in {"PLACED", "MATCHED", "DRY_RUN"}

    def to_row(self) -> Dict:
        return asdict(self)


@dataclass
class FairLine:
    """A fair (de-vigged) probability estimate for one event/market, from the
    truth source (Pinnacle). ``probs`` maps selection name -> win probability and
    sums to ~1.0."""

    event_key: str          # truth-source event id
    sport_key: str
    commence_time: str
    home_team: str
    away_team: str
    market: str
    probs: Dict[str, float] = field(default_factory=dict)
    source: str = "pinnacle"
    last_update: Optional[str] = None  # ISO timestamp of the underlying line

    def fair_price(self, selection: str) -> Optional[float]:
        p = self.probs.get(selection)
        return (1.0 / p) if p and p > 0 else None


@dataclass
class VenueQuote:
    """A back price available on the betting venue (Betfair Exchange) for one
    runner, with the ids needed to place on it directly."""

    venue: str               # "betfair"
    market_id: str
    selection_id: str
    runner_name: str
    price: float             # best decimal back price available
    size: float              # amount available to back at that price
    event_name: str
    home_team: str
    away_team: str
    commence_time: str
    market: str              # e.g. "h2h"
