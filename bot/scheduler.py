"""Continuous, near-kickoff scheduler.

The sharpest, most accurate line is the one just before the off, so the bot
should bet **as late as it safely can**. This runner loops forever:

  1. re-evaluate value with fresh data every cycle,
  2. place only the bets whose event starts within ``place_window`` (and hasn't
     started yet), so we always act on the latest, sharpest prices,
  3. sleep adaptively — long when nothing is near kickoff, tight (a few seconds)
     when an event is inside its placement window — to minimise both API load
     and the latency between pricing and placement,
  4. keep the Betfair session alive, and never bet the same selection twice
     (dedup is handled by the store).

``now_fn`` / ``sleep_fn`` / ``max_cycles`` are injectable for testing.
"""
from __future__ import annotations

import datetime as _dt
import logging
import time
from typing import Callable, List, Optional

from .models import ValueBet

log = logging.getLogger("value_bot.scheduler")


def _to_epoch(commence_time: str) -> Optional[float]:
    if not commence_time:
        return None
    try:
        dt = _dt.datetime.fromisoformat(commence_time.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_dt.timezone.utc)
    return dt.timestamp()


class ContinuousRunner:
    def __init__(
        self,
        bot,
        poll_interval: float = 60.0,        # cadence when nothing is near kickoff
        refresh_interval: float = 5.0,      # cadence when an event is in-window
        place_window_minutes: float = 3.0,  # start betting this long before the off
        min_seconds_before_start: float = 20.0,  # stop betting this close to the off
        keepalive_every_cycles: int = 15,
        now_fn: Callable[[], float] = time.time,
        sleep_fn: Callable[[float], None] = time.sleep,
        max_cycles: Optional[int] = None,
    ):
        self.bot = bot
        self.poll_interval = poll_interval
        self.refresh_interval = refresh_interval
        self.place_window = place_window_minutes * 60.0
        self.min_seconds_before_start = min_seconds_before_start
        self.keepalive_every_cycles = keepalive_every_cycles
        self.now_fn = now_fn
        self.sleep_fn = sleep_fn
        self.max_cycles = max_cycles
        self._stop = False

    def stop(self) -> None:
        self._stop = True

    def _seconds_to_start(self, bet: ValueBet) -> Optional[float]:
        epoch = _to_epoch(bet.commence_time)
        return None if epoch is None else epoch - self.now_fn()

    def _is_due(self, bet: ValueBet) -> bool:
        """In the placement window and not yet (basically) started."""
        s = self._seconds_to_start(bet)
        if s is None:
            return True  # unknown start time -> act now rather than never
        return self.min_seconds_before_start <= s <= self.place_window

    def _next_sleep(self, bets: List[ValueBet]) -> float:
        """Short sleep if anything is in-window; otherwise sleep until the next
        event is about to enter its window (capped at poll_interval)."""
        in_window = False
        soonest_enter = self.poll_interval
        for bet in bets:
            s = self._seconds_to_start(bet)
            if s is None:
                continue
            if self.min_seconds_before_start <= s <= self.place_window:
                in_window = True
            elif s > self.place_window:
                soonest_enter = min(soonest_enter, s - self.place_window)
        if in_window:
            return self.refresh_interval
        return max(1.0, min(soonest_enter, self.poll_interval))

    def run_once(self) -> List:
        """One evaluate-and-place cycle. Returns the placement results."""
        bets = self.bot.evaluate()
        due = [b for b in bets if self._is_due(b)]
        results = self.bot.place_bets(due) if due else []
        # Stash for the sleep calculation (so callers/tests can inspect, too).
        self._last_bets = bets
        return results

    def run(self) -> None:
        log.info("continuous runner started (place window %.0fs before start, "
                 "poll %.0fs / refresh %.0fs)",
                 self.place_window, self.poll_interval, self.refresh_interval)
        cycle = 0
        while not self._stop:
            cycle += 1
            try:
                self.run_once()
            except Exception as exc:  # never let one bad cycle kill the loop
                log.error("cycle %d failed: %s", cycle, exc)
                self._last_bets = []
            if self.keepalive_every_cycles and cycle % self.keepalive_every_cycles == 0:
                self.bot.keep_alive()
            if self.max_cycles is not None and cycle >= self.max_cycles:
                break
            self.sleep_fn(self._next_sleep(getattr(self, "_last_bets", [])))
        log.info("continuous runner stopped after %d cycle(s)", cycle)
