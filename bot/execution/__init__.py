"""Bet executors: place a sized ValueBet at a venue and report the result."""
from .base import Executor
from .paper import PaperExecutor

__all__ = ["Executor", "PaperExecutor", "get_betfair_executor"]


def get_betfair_executor(*args, **kwargs):
    """Lazy accessor so importing this package never requires betfairlightweight."""
    from .betfair import BetfairExecutor

    return BetfairExecutor(*args, **kwargs)
