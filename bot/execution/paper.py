"""Paper (simulated) executor — the safe default.

Places nothing real. It simulates a fill at the requested price (optionally
applying slippage and a fill probability so paper results aren't unrealistically
perfect) and returns a PlacementResult so the rest of the pipeline — logging,
settlement, reporting — behaves identically to live trading.
"""
from __future__ import annotations

import random
import uuid

from ..models import PlacementResult, ValueBet


class PaperExecutor:
    name = "paper"

    def __init__(self, slippage: float = 0.0, fill_probability: float = 1.0, seed=None):
        self.slippage = slippage              # e.g. 0.01 -> take 1% worse price
        self.fill_probability = fill_probability
        self._rng = random.Random(seed)

    def place(self, bet: ValueBet) -> PlacementResult:
        ref = f"paper-{uuid.uuid4().hex[:12]}"
        if self._rng.random() > self.fill_probability:
            return PlacementResult(
                bet_key=bet.key,
                executor=self.name,
                status="REJECTED",
                requested_price=bet.price,
                requested_stake=bet.stake,
                external_ref=ref,
                message="simulated no-fill (price moved before match)",
            )
        matched_price = round(bet.price * (1.0 - self.slippage), 4)
        return PlacementResult(
            bet_key=bet.key,
            executor=self.name,
            status="MATCHED",
            requested_price=bet.price,
            requested_stake=bet.stake,
            matched_price=matched_price,
            matched_stake=bet.stake,
            external_ref=ref,
            message="paper fill",
        )

    def close(self) -> None:
        pass
