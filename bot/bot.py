"""Orchestration: wire providers, detector, bankroll, executor and store together.

Pipeline per run:
  1. fetch odds  -> MarketBoards
  2. detect      -> ValueBets (+EV)
  3. assign      -> stakes (fractional Kelly + caps)
  4. log         -> every identified value bet
  5. place       -> through the configured executor (paper unless live)
  6. log         -> every placement result

The bot NEVER places real money unless config.live is True AND the executor is a
live one. The default executor is paper.
"""
from __future__ import annotations

import logging
from typing import List, Tuple

from .bankroll import BankrollManager
from .config import Config
from .execution import PaperExecutor, get_betfair_executor
from .execution.base import Executor
from .models import PlacementResult, ValueBet
from .providers import SampleProvider, TheOddsAPIProvider
from .providers.base import OddsProvider
from .store import BetStore
from .value import ValueDetector

log = logging.getLogger("value_bot")


def build_provider(cfg: Config) -> OddsProvider:
    if cfg.provider == "the_odds_api":
        return TheOddsAPIProvider(api_key=cfg.odds_api_key or "", regions=cfg.regions)
    if cfg.provider == "sample":
        return SampleProvider()
    raise ValueError(f"unknown provider {cfg.provider!r}")


def build_executor(cfg: Config) -> Executor:
    """Return the configured executor, enforcing the live-money safety gate.

    A live (betfair) executor is only constructed when cfg.live is True.
    Otherwise we hard-fall-back to paper, regardless of cfg.executor, so a
    misconfiguration can never silently bet real money.
    """
    if cfg.executor == "betfair" and cfg.live:
        log.warning("LIVE Betfair executor selected (dry_run=%s)", cfg.betfair_dry_run)
        return get_betfair_executor(
            username=cfg.betfair_username,
            password=cfg.betfair_password,
            app_key=cfg.betfair_app_key,
            certs_path=cfg.betfair_certs_path,
            dry_run=cfg.betfair_dry_run,
        )
    if cfg.executor == "betfair" and not cfg.live:
        log.warning("executor=betfair but live=False -> using PAPER executor")
    return PaperExecutor(
        slippage=cfg.paper_slippage,
        fill_probability=cfg.paper_fill_probability,
    )


class ValueBettingBot:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.provider = build_provider(cfg)
        self.detector = ValueDetector(
            reference_books=cfg.reference_books,
            devig_method=cfg.devig_method,
            min_edge=cfg.min_edge,
            min_price=cfg.min_price,
            max_price=cfg.max_price,
        )
        self.bankroll = BankrollManager(
            bankroll=cfg.bankroll,
            kelly_multiplier=cfg.kelly_multiplier,
            max_fraction_per_bet=cfg.max_fraction_per_bet,
            min_stake=cfg.min_stake,
            max_stake=cfg.max_stake,
            max_total_exposure_fraction=cfg.max_total_exposure_fraction,
        )
        self.store = BetStore(db_path=cfg.db_path, csv_path=cfg.csv_path)

    # -- identification only ----------------------------------------------
    def scan(self) -> List[ValueBet]:
        boards = []
        for sport in self.cfg.sports:
            try:
                boards.extend(self.provider.fetch(sport, self.cfg.markets))
            except Exception as exc:
                log.error("fetch failed for %s: %s", sport, exc)
        bets = self.detector.detect(boards)
        staked = self.bankroll.assign(bets)
        log.info("scanned %d boards -> %d value bets, %d stakeable",
                 len(boards), len(bets), len(staked))
        return staked

    # -- identify + place + log -------------------------------------------
    def run(self) -> List[Tuple[ValueBet, PlacementResult]]:
        bets = self.scan()
        for bet in bets:
            self.store.log_value_bet(bet)

        executor = build_executor(self.cfg)
        results: List[Tuple[ValueBet, PlacementResult]] = []
        try:
            for bet in bets:
                result = executor.place(bet)
                self.store.log_placement(result)
                results.append((bet, result))
                log.info("%s %s @ %.2f stake %.2f -> %s (%s)",
                         bet.bookmaker, bet.selection, bet.price, bet.stake,
                         result.status, result.message)
        finally:
            executor.close()
        return results

    def close(self) -> None:
        self.store.close()
