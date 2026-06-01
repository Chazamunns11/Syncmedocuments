"""Offline sample provider.

Returns a deterministic set of market boards so the bot can be run, tested and
demoed without an API key or network access. One board is deliberately seeded
with a soft book pricing a selection above the sharp (Pinnacle) fair line, so
the detector finds a value bet.
"""
from __future__ import annotations

from typing import List

from ..models import BookOdds, MarketBoard, Outcome
from .base import OddsProvider


class SampleProvider(OddsProvider):
    name = "sample"

    def fetch(self, sport_key: str, markets: List[str]) -> List[MarketBoard]:
        boards: List[MarketBoard] = []

        # Event 1: a clear value spot. Pinnacle (sharp) ~ fair 50/50 after vig;
        # "softbook" is offering 2.15 on the home side -> well above fair 2.0.
        boards.append(
            MarketBoard(
                event_id="evt_demo_1",
                sport_key=sport_key,
                commence_time="2026-06-02T18:00:00Z",
                home_team="Arsenal",
                away_team="Chelsea",
                market="h2h",
                books=[
                    BookOdds("pinnacle", "h2h", [
                        Outcome("Arsenal", 1.95),
                        Outcome("Chelsea", 1.95),
                    ]),
                    BookOdds("softbook", "h2h", [
                        Outcome("Arsenal", 2.15),   # value: fair ~2.00
                        Outcome("Chelsea", 1.80),
                    ]),
                    BookOdds("anotherbook", "h2h", [
                        Outcome("Arsenal", 2.02),
                        Outcome("Chelsea", 1.88),
                    ]),
                ],
            )
        )

        # Event 2: efficient market, no value (every book near the sharp line).
        boards.append(
            MarketBoard(
                event_id="evt_demo_2",
                sport_key=sport_key,
                commence_time="2026-06-02T20:00:00Z",
                home_team="Liverpool",
                away_team="Everton",
                market="h2h",
                books=[
                    BookOdds("pinnacle", "h2h", [
                        Outcome("Liverpool", 1.50),
                        Outcome("Everton", 2.70),
                    ]),
                    BookOdds("softbook", "h2h", [
                        Outcome("Liverpool", 1.48),
                        Outcome("Everton", 2.65),
                    ]),
                ],
            )
        )

        return [b for b in boards if b.market in markets]
