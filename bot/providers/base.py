"""Odds provider interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from ..models import MarketBoard


class OddsProvider(ABC):
    """A source of bookmaker odds, normalised into MarketBoard objects."""

    name: str = "base"

    @abstractmethod
    def fetch(self, sport_key: str, markets: List[str]) -> List[MarketBoard]:
        """Return one MarketBoard per (event, market) combination."""
        raise NotImplementedError
