"""Sharp line-movement tracking.

Betfair is itself a very sharp price, so a static "Betfair beats fair" gap is
thin and often a trap. The real exploitable moment is when the SHARP consensus
(Pinnacle / weighted books) has just MOVED but Betfair hasn't caught up yet —
you take Betfair's stale price before it converges.

This keeps a short, in-memory time-series of the fair (sharp) probability and the
Betfair price per (event, selection), and reports how the sharp line has moved
over a lookback window:

* ``d_prob > 0`` — the sharp now rates your selection MORE likely (fair price
  shortened) while you can still back it at the old price → favourable lag.
* ``d_prob < 0`` — the sharp is moving AWAY from your selection → the apparent
  value is a falling knife; don't bet, you'd be picked off.

History is in-memory (rebuilds within one window after a restart).
"""
from __future__ import annotations

import time
from collections import deque
from typing import Deque, Dict, Optional, Tuple


class LineTracker:
    def __init__(self, max_age_seconds: float = 3600.0, max_points: int = 60):
        self.max_age = max_age_seconds
        self.max_points = max_points
        # key -> deque[(ts, fair_prob, betfair_price)]
        self._hist: Dict[str, Deque[Tuple[float, float, float]]] = {}

    @staticmethod
    def key(event_id: str, selection: str) -> str:
        return f"{event_id}|{selection}"

    def update(self, key: str, fair_prob: float, betfair_price: Optional[float],
               now: Optional[float] = None) -> None:
        now = time.time() if now is None else now
        dq = self._hist.setdefault(key, deque(maxlen=self.max_points))
        dq.append((now, fair_prob, betfair_price if betfair_price else 0.0))
        # Drop points older than max_age.
        while dq and now - dq[0][0] > self.max_age:
            dq.popleft()

    def move(self, key: str, window_seconds: float,
             now: Optional[float] = None) -> Optional[Tuple[float, float]]:
        """Return (d_prob, d_betfair) = latest - earliest-within-window for the
        sharp fair probability and the Betfair price. None if there isn't enough
        history within the window to judge a move."""
        now = time.time() if now is None else now
        dq = self._hist.get(key)
        if not dq:
            return None
        latest = dq[-1]
        earliest = None
        for point in dq:
            if now - point[0] <= window_seconds:
                earliest = point
                break
        if earliest is None or earliest is latest:
            return None
        return latest[1] - earliest[1], latest[2] - earliest[2]

    def prune(self, now: Optional[float] = None) -> None:
        now = time.time() if now is None else now
        for key in list(self._hist):
            dq = self._hist[key]
            while dq and now - dq[0][0] > self.max_age:
                dq.popleft()
            if not dq:
                del self._hist[key]
