"""Bet executors: place a sized ValueBet at a venue and report the result.

``BetfairExecutor`` is intentionally NOT imported here so this package never
requires ``betfairlightweight``; import it lazily from ``bot.execution.betfair``.
"""
from .base import Executor
from .paper import PaperExecutor

__all__ = ["Executor", "PaperExecutor"]
