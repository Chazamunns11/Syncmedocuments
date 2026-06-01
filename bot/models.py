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


@dataclass
class BookOdds:
    """One bookmaker's prices for one market of one event."""

    bookmaker: str
    market: str  # e.g. "h2h", "spreads", "totals"
    outcomes: List[Outcome]
    last_update: Optional[str] = None

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
    ev: float                # expected profit per 1 unit staked
    kelly_fraction: float    # fraction of bankroll suggested (pre-cap)
    stake: float = 0.0       # actual stake assigned by bankroll manager
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
