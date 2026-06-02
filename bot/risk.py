"""Risk management & circuit breakers.

Surviving variance is the single biggest determinant of whether an edge ever
turns into money. This module sits between staking and placement and can:

* **halt** all betting on a drawdown stop-loss (peak-to-now), a bankroll floor,
  a daily stake cap, a daily bet-count cap, or too many open positions;
* **cap** an individual stake to the remaining daily budget and the remaining
  open-exposure budget.

State (peak bankroll) is persisted in the store so the breakers survive restarts.
"""
from __future__ import annotations

import datetime as _dt
import logging
from dataclasses import dataclass
from typing import Tuple

log = logging.getLogger("value_bot.risk")


def _start_of_utc_day() -> str:
    now = _dt.datetime.now(_dt.timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()


@dataclass
class RiskLimits:
    starting_bankroll: float
    daily_stake_limit_fraction: float = 0.25   # max staked per day vs bankroll
    max_open_bets: int = 25                     # max simultaneous open positions
    max_open_exposure_fraction: float = 0.25    # max staked-but-unsettled vs bankroll
    max_bets_per_day: int = 200
    stop_loss_fraction: float = 0.30            # halt if drawdown from peak exceeds
    min_bankroll_fraction: float = 0.50         # halt if bankroll falls below this


class RiskManager:
    def __init__(self, limits: RiskLimits, store):
        self.limits = limits
        self.store = store
        self._halted_reason = None

    # -- breakers ----------------------------------------------------------
    def status(self, bankroll: float) -> Tuple[bool, str]:
        """Return (ok_to_bet, reason). Updates the persisted peak bankroll."""
        L = self.limits
        peak = max(self.store.get_meta("peak_bankroll", L.starting_bankroll), bankroll)
        self.store.set_meta("peak_bankroll", peak)

        if bankroll < L.min_bankroll_fraction * L.starting_bankroll:
            return False, (f"bankroll {bankroll:.2f} below floor "
                           f"{L.min_bankroll_fraction*L.starting_bankroll:.2f}")
        if peak > 0 and (peak - bankroll) / peak > L.stop_loss_fraction:
            return False, (f"drawdown {(peak-bankroll)/peak*100:.1f}% from peak "
                           f"{peak:.2f} exceeds stop-loss {L.stop_loss_fraction*100:.0f}%")
        day = _start_of_utc_day()
        if self.store.count_since(day) >= L.max_bets_per_day:
            return False, f"daily bet count limit ({L.max_bets_per_day}) reached"
        if self.store.staked_since(day) >= L.daily_stake_limit_fraction * bankroll:
            return False, "daily stake limit reached"
        if self.store.count_open() >= L.max_open_bets:
            return False, f"max open bets ({L.max_open_bets}) reached"
        return True, "ok"

    # -- per-bet stake cap -------------------------------------------------
    def cap_stake(self, stake: float, bankroll: float) -> float:
        """Reduce a stake so it respects the remaining daily and open-exposure
        budgets. Returns 0 if no budget remains."""
        L = self.limits
        day = _start_of_utc_day()
        daily_budget = max(0.0, L.daily_stake_limit_fraction * bankroll
                           - self.store.staked_since(day))
        exposure_budget = max(0.0, L.max_open_exposure_fraction * bankroll
                              - self.store.open_exposure())
        return max(0.0, min(stake, daily_budget, exposure_budget))
