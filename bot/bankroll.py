"""Bankroll management and stake assignment.

Turns each value bet's (pre-cap) Kelly fraction into a concrete stake, applying:

* a fractional-Kelly multiplier (full Kelly is too aggressive in practice and
  assumes your probability estimate is exact — it never is),
* a per-bet cap as a fraction of bankroll,
* an absolute minimum/maximum stake,
* a ceiling on the total amount staked in a single run.

Stakes are rounded to a sensible currency precision.
"""
from __future__ import annotations

from typing import List, Optional

from .models import ValueBet


class BankrollManager:
    def __init__(
        self,
        bankroll: float,
        kelly_multiplier: float = 0.25,  # quarter-Kelly: standard conservative choice
        max_fraction_per_bet: float = 0.02,
        min_stake: float = 1.0,
        max_stake: float = 250.0,
        max_total_exposure_fraction: float = 0.10,
        round_to: float = 0.01,
        flat_stake: Optional[float] = None,
    ):
        if bankroll <= 0:
            raise ValueError("bankroll must be positive")
        self.bankroll = float(bankroll)
        self.kelly_multiplier = kelly_multiplier
        self.max_fraction_per_bet = max_fraction_per_bet
        self.min_stake = min_stake
        self.max_stake = max_stake
        self.max_total_exposure_fraction = max_total_exposure_fraction
        self.round_to = round_to
        # When set, every bet stakes this fixed amount (the Kaunitz / practitioner
        # constant-stake approach) instead of Kelly sizing.
        self.flat_stake = flat_stake

    def _round(self, x: float) -> float:
        if self.round_to <= 0:
            return x
        return round(x / self.round_to) * self.round_to

    def stake_for(self, bet: ValueBet) -> float:
        if self.flat_stake is not None:
            stake = self.flat_stake
        else:
            frac = bet.kelly_fraction * self.kelly_multiplier
            frac = min(frac, self.max_fraction_per_bet)
            stake = frac * self.bankroll
        stake = min(stake, self.max_stake)
        # Never stake more than is available to back at the venue price: a
        # larger order would partially fill at worse prices and erode the edge.
        if bet.available_size is not None:
            stake = min(stake, bet.available_size)
        if stake < self.min_stake:
            return 0.0
        return self._round(stake)

    def assign(self, bets: List[ValueBet]) -> List[ValueBet]:
        """Assign stakes in-place (best edge first) honouring the total exposure
        cap. Bets that would breach the cap, or round below ``min_stake``, get a
        stake of 0 and are filtered out."""
        budget = self.max_total_exposure_fraction * self.bankroll
        spent = 0.0
        staked: List[ValueBet] = []
        for bet in sorted(bets, key=lambda b: b.edge, reverse=True):
            stake = self.stake_for(bet)
            if stake <= 0:
                continue
            if spent + stake > budget:
                stake = self._round(budget - spent)
                if stake < self.min_stake:
                    continue
            bet.stake = stake
            spent += stake
            staked.append(bet)
        return staked
