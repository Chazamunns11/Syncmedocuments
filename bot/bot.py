"""Orchestration: wire sources, detector, bankroll, executor and store together.

Two pipeline modes (config.mode):

* ``pinnacle_betfair`` (recommended) — get the fair line from Pinnacle (source
  of truth), get back prices from Betfair Exchange, match the events, value the
  Betfair prices net of commission, and place the +EV ones on Betfair. The right
  choice if you're limited/banned on the soft books.

* ``multi_book`` — classic single-feed cross-bookmaker value scan.

Per run: fetch -> detect -> stake -> log(identified) -> place -> log(placement).

Safety: real money is only ever placed when ``live`` is True AND the executor is
a live one. Any other configuration falls back to the paper executor.
"""
from __future__ import annotations

import logging
from typing import List, Optional, Tuple

from .bankroll import BankrollManager
from .betfair_client import EVENT_TYPE_IDS, BetfairClient
from .config import Config
from .execution import PaperExecutor
from .execution.base import Executor
from .matcher import EventMatcher
from .models import FairLine, MarketBoard, PlacementResult, ValueBet, VenueQuote
from .pinnacle import PinnacleClient, pinnacle_lines_via_odds_api
from .providers import SampleProvider, TheOddsAPIProvider
from .samples import sample_betfair_quotes, sample_pinnacle_lines
from .store import BetStore

log = logging.getLogger("value_bot")


def build_executor(cfg: Config, betfair_client: Optional[BetfairClient] = None) -> Executor:
    """Construct the configured executor, enforcing the live-money safety gate.

    A live Betfair executor is only built when ``cfg.live`` is True; any other
    configuration falls back to the paper executor so a misconfiguration can
    never silently place real bets.
    """
    if cfg.executor == "betfair" and cfg.live:
        from .execution.betfair import BetfairExecutor
        log.warning("LIVE Betfair executor selected (dry_run=%s)", cfg.betfair_dry_run)
        return BetfairExecutor(
            client=betfair_client or BetfairClient(
                username=cfg.betfair_username or "",
                password=cfg.betfair_password or "",
                app_key=cfg.betfair_app_key or "",
                certs_path=cfg.betfair_certs_path,
            ),
            dry_run=cfg.betfair_dry_run,
        )
    if cfg.executor == "betfair" and not cfg.live:
        log.warning("executor=betfair but live=False -> using PAPER executor")
    return PaperExecutor(slippage=cfg.paper_slippage,
                         fill_probability=cfg.paper_fill_probability)


class ValueBettingBot:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        commission = cfg.betfair_commission if cfg.mode == "pinnacle_betfair" else 0.0
        self.detector_kwargs = dict(
            reference_books=cfg.reference_books,
            devig_method=cfg.devig_method,
            min_edge=cfg.min_edge,
            min_price=cfg.min_price,
            max_price=cfg.max_price,
            commission=commission,
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
        # A single Betfair session shared between the price source and executor.
        self._betfair: Optional[BetfairClient] = None

    # -- betfair session ---------------------------------------------------
    def _betfair_client(self) -> BetfairClient:
        if self._betfair is None:
            self._betfair = BetfairClient(
                username=self.cfg.betfair_username or "",
                password=self.cfg.betfair_password or "",
                app_key=self.cfg.betfair_app_key or "",
                certs_path=self.cfg.betfair_certs_path,
            )
        return self._betfair

    # -- truth source: Pinnacle -------------------------------------------
    def _fair_lines(self) -> List[FairLine]:
        src = self.cfg.pinnacle_source
        lines: List[FairLine] = []
        if src == "sample":
            return sample_pinnacle_lines(self.cfg.pinnacle_sports[0])
        for sport in self.cfg.pinnacle_sports:
            try:
                if src == "the_odds_api":
                    lines.extend(pinnacle_lines_via_odds_api(
                        api_key=self.cfg.odds_api_key or "", sport_key=sport,
                        regions=self.cfg.regions, devig_method=self.cfg.devig_method,
                    ))
                elif src == "direct":
                    client = PinnacleClient(
                        self.cfg.pinnacle_username or "",
                        self.cfg.pinnacle_password or "",
                    )
                    lines.extend(client.fair_lines(sport, self.cfg.devig_method))
                else:
                    raise ValueError(f"unknown pinnacle_source {src!r}")
            except Exception as exc:
                log.error("pinnacle fetch failed for %s: %s", sport, exc)
        return lines

    # -- venue source: Betfair --------------------------------------------
    def _venue_quotes(self) -> List[VenueQuote]:
        if self.cfg.venue_source == "sample":
            return sample_betfair_quotes()
        if self.cfg.venue_source == "betfair":
            event_type = EVENT_TYPE_IDS.get(self.cfg.betfair_event_type)
            if not event_type:
                raise ValueError(f"unknown betfair_event_type {self.cfg.betfair_event_type!r}")
            try:
                return self._betfair_client().list_match_odds(
                    event_type_id=event_type,
                    competition_ids=self.cfg.betfair_competition_ids or None,
                    market_start_within_hours=self.cfg.betfair_market_start_within_hours,
                )
            except Exception as exc:
                log.error("betfair price fetch failed: %s", exc)
                return []
        raise ValueError(f"unknown venue_source {self.cfg.venue_source!r}")

    # -- board construction ------------------------------------------------
    def _boards(self) -> List[MarketBoard]:
        if self.cfg.mode == "pinnacle_betfair":
            fair = self._fair_lines()
            quotes = self._venue_quotes()
            boards = EventMatcher(
                min_team_score=self.cfg.match_min_team_score,
                start_window_minutes=self.cfg.match_start_window_minutes,
            ).build_boards(fair, quotes)
            log.info("pinnacle lines=%d, betfair quotes=%d -> %d matched boards",
                     len(fair), len(quotes), len(boards))
            return boards
        if self.cfg.mode == "multi_book":
            provider = (TheOddsAPIProvider(api_key=self.cfg.odds_api_key or "",
                                           regions=self.cfg.regions)
                        if self.cfg.provider == "the_odds_api" else SampleProvider())
            boards: List[MarketBoard] = []
            for sport in self.cfg.sports:
                try:
                    boards.extend(provider.fetch(sport, self.cfg.markets))
                except Exception as exc:
                    log.error("fetch failed for %s: %s", sport, exc)
            return boards
        raise ValueError(f"unknown mode {self.cfg.mode!r}")

    # -- executor (with live-money safety gate) ---------------------------
    def _build_executor(self) -> Executor:
        client = self._betfair_client() if (
            self.cfg.executor == "betfair" and self.cfg.live) else None
        return build_executor(self.cfg, betfair_client=client)

    # -- identification only ----------------------------------------------
    def scan(self) -> List[ValueBet]:
        from .value import ValueDetector
        boards = self._boards()
        bets = ValueDetector(**self.detector_kwargs).detect(boards)
        staked = self.bankroll.assign(bets)
        log.info("%d boards -> %d value bets, %d stakeable",
                 len(boards), len(bets), len(staked))
        return staked

    # -- identify + place + log -------------------------------------------
    def run(self) -> List[Tuple[ValueBet, PlacementResult]]:
        bets = self.scan()
        for bet in bets:
            self.store.log_value_bet(bet)

        executor = self._build_executor()
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
        if self._betfair is not None:
            self._betfair.close()
        self.store.close()
