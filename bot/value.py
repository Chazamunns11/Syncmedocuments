"""Value detection and Kelly stake sizing.

The detector estimates a *fair* probability for each outcome by de-vigging a
trusted "sharp" reference bookmaker (Pinnacle by default), then scans every
other bookmaker's price for that outcome. Where the offered decimal price beats
the fair price by more than a threshold, that's a +EV ("value") bet.

Why a sharp reference book? Soft books shade their lines and move slowly; sharp
books like Pinnacle price close to the true probability and take large bets, so
their de-vigged line is the best cheap estimate of "truth" available. If the
reference book is missing for a market we fall back to the de-vigged consensus
of all books.
"""
from __future__ import annotations

import statistics
from typing import List, Optional

from .devig import devig
from .models import MarketBoard, ValueBet


def kelly_fraction(prob: float, price: float) -> float:
    """Full-Kelly fraction of bankroll for a bet at decimal ``price`` with win
    probability ``prob``. Returns 0 for non-positive-edge bets.

    f* = (b*p - q) / b, where b = price - 1, q = 1 - p.
    """
    b = price - 1.0
    if b <= 0:
        return 0.0
    q = 1.0 - prob
    f = (b * prob - q) / b
    return max(0.0, f)


def expected_value(prob: float, price: float) -> float:
    """Expected profit per 1 unit staked: p*(price-1) - (1-p)."""
    return prob * (price - 1.0) - (1.0 - prob)


def _fair_probs(
    board: MarketBoard,
    reference_books: List[str],
    method: str,
) -> Optional[dict]:
    """Return {selection: fair_prob} from the first available reference book,
    else from the de-vigged consensus across all books. None if unusable."""
    selections = board.selections()

    def from_book(book) -> Optional[dict]:
        odds = [book.price_for(s) for s in selections]
        if any(o is None for o in odds):
            return None
        try:
            fair = devig(odds, method=method)
        except ValueError:
            return None
        return dict(zip(selections, fair))

    by_name = {b.bookmaker.lower(): b for b in board.books}
    for ref in reference_books:
        book = by_name.get(ref.lower())
        if book is not None:
            res = from_book(book)
            if res:
                return res

    # Consensus fallback: average de-vigged probability across every book that
    # quotes the full set of selections.
    per_selection: dict = {s: [] for s in selections}
    used = 0
    for book in board.books:
        res = from_book(book)
        if res:
            used += 1
            for s, p in res.items():
                per_selection[s].append(p)
    if used == 0:
        return None
    consensus = {s: statistics.mean(v) for s, v in per_selection.items() if v}
    total = sum(consensus.values())
    if total <= 0:
        return None
    return {s: p / total for s, p in consensus.items()}


class ValueDetector:
    """Finds +EV bets across a collection of market boards."""

    def __init__(
        self,
        reference_books: Optional[List[str]] = None,
        devig_method: str = "multiplicative",
        min_edge: float = 0.02,
        min_price: float = 1.30,
        max_price: float = 15.0,
        exclude_books: Optional[List[str]] = None,
        commission: float = 0.0,
    ):
        # Reference (sharp) books in priority order.
        self.reference_books = reference_books or ["pinnacle"]
        self.devig_method = devig_method
        self.min_edge = min_edge          # require price/fair_price - 1 >= this
        self.min_price = min_price        # ignore very short prices
        self.max_price = max_price        # ignore lottery longshots
        # Commission charged on net winnings at the betting venue (e.g. Betfair
        # ~2-5%). The edge/EV/Kelly are computed on the commission-adjusted
        # ("effective") price so the bot only bets when value survives the rake.
        self.commission = commission
        # Never flag the reference book against itself.
        self.exclude_books = {b.lower() for b in (exclude_books or [])}
        self.exclude_books |= {b.lower() for b in self.reference_books}

    def _effective_price(self, price: float) -> float:
        """Decimal odds after commission on net winnings: a winning back bet at
        ``price`` returns (price-1)*(1-commission) profit per unit staked."""
        if self.commission <= 0:
            return price
        return 1.0 + (price - 1.0) * (1.0 - self.commission)

    def detect_board(self, board: MarketBoard) -> List[ValueBet]:
        fair = _fair_probs(board, self.reference_books, self.devig_method)
        if not fair:
            return []

        found: List[ValueBet] = []
        for book in board.books:
            if book.bookmaker.lower() in self.exclude_books:
                continue
            for outcome in book.outcomes:
                p = fair.get(outcome.name)
                if p is None or p <= 0:
                    continue
                price = outcome.price
                if price < self.min_price or price > self.max_price:
                    continue
                eff_price = self._effective_price(price)
                fair_price = 1.0 / p
                # Edge and EV are measured on the commission-adjusted price.
                edge = eff_price / fair_price - 1.0
                if edge < self.min_edge:
                    continue
                ev = expected_value(p, eff_price)
                if ev <= 0:
                    continue
                found.append(
                    ValueBet(
                        event_id=board.event_id,
                        sport_key=board.sport_key,
                        commence_time=board.commence_time,
                        matchup=f"{board.home_team} vs {board.away_team}",
                        market=board.market,
                        selection=outcome.name,
                        bookmaker=book.bookmaker,
                        price=price,
                        fair_prob=p,
                        fair_price=fair_price,
                        edge=edge,
                        ev=ev,
                        kelly_fraction=kelly_fraction(p, eff_price),
                        commission=self.commission,
                        eff_price=eff_price,
                        venue_market_id=book.market_id,
                        venue_selection_id=outcome.selection_id,
                    )
                )
        return found

    def detect(self, boards: List[MarketBoard]) -> List[ValueBet]:
        bets: List[ValueBet] = []
        for board in boards:
            bets.extend(self.detect_board(board))
        # Best edge first.
        bets.sort(key=lambda b: b.edge, reverse=True)
        return bets
