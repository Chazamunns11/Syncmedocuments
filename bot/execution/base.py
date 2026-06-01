"""Executor interface."""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import PlacementResult, ValueBet


class Executor(ABC):
    name: str = "base"

    @abstractmethod
    def place(self, bet: ValueBet) -> PlacementResult:
        """Attempt to place ``bet`` and return a PlacementResult."""
        raise NotImplementedError

    def close(self) -> None:  # optional cleanup hook
        pass
