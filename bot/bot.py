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
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional, Tuple

from .bankroll import BankrollManager
from .betfair_client import EVENT_TYPE_IDS, BetfairClient
from .config import Config
from .consensus import consensus_lines_from_boards, consensus_lines_via_odds_api
from .execution import PaperExecutor
from .execution.base import Executor
from .matcher import EventMatcher
from .models import FairLine, MarketBoard, PlacementResult, ValueBet, VenueQuote
from .notify import Notifier
from .pinnacle import PinnacleClient, pinnacle_lines_via_odds_api
from .providers import SampleProvider, TheOddsAPIProvider
from .risk import RiskLimits, RiskManager
from .samples import (sample_betfair_quotes, sample_multibook_boards,
                      sample_pinnacle_lines)
from .store import BetStore

log = logging.getLogger("value_bot")


def _pair_key(fl: FairLine) -> tuple:
    """Source-independent event identity: the sorted normalised team pair."""
    from .aliases import normalize
    return tuple(sorted((normalize(fl.home_team), normalize(fl.away_team))))


def _blend(pinnacle: List[FairLine], consensus: List[FairLine]) -> List[FairLine]:
    """Average the pinnacle and weighted-consensus fair probabilities per event.

    Events are matched across the two sources by normalised team pair (not raw
    event key, which differs between feeds). Events in only one source are kept."""
    by_pair = {_pair_key(fl): fl for fl in consensus}
    out: List[FairLine] = []
    used = set()
    for p in pinnacle:
        key = _pair_key(p)
        c = by_pair.get(key)
        if c is None:
            out.append(p)
            continue
        used.add(key)
        sels = set(p.probs) | set(c.probs)
        probs = {}
        for s in sels:
            vals = [v for v in (p.probs.get(s), c.probs.get(s)) if v is not None]
            probs[s] = sum(vals) / len(vals)
        overs = [o for o in (p.overround, c.overround) if o is not None]
        out.append(FairLine(
            event_key=p.event_key, sport_key=p.sport_key,
            commence_time=p.commence_time, home_team=p.home_team,
            away_team=p.away_team, market=p.market, probs=probs,
            source="blend", last_update=p.last_update,
            overround=(sum(overs) / len(overs)) if overs else None))
    out.extend(c for k, c in by_pair.items() if k not in used)
    return out


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
            edge_haircut=cfg.edge_haircut,
            min_liquidity=cfg.min_liquidity,
            max_overround=cfg.max_overround,
            min_expected_clv=cfg.min_expected_clv,
            one_per_event=cfg.one_bet_per_event,
        )
        self.bankroll = BankrollManager(
            bankroll=cfg.bankroll,
            kelly_multiplier=cfg.kelly_multiplier,
            max_fraction_per_bet=cfg.max_fraction_per_bet,
            min_stake=cfg.min_stake,
            max_stake=cfg.max_stake,
            max_total_exposure_fraction=cfg.max_total_exposure_fraction,
            flat_stake=cfg.flat_stake,
        )
        self.store = BetStore(db_path=cfg.db_path, csv_path=cfg.csv_path)
        self.notifier = Notifier(webhook_url=cfg.notify_webhook_url,
                                 on_bets=cfg.notify_on_bets,
                                 on_halt=cfg.notify_on_halt)
        self.risk = RiskManager(RiskLimits(
            starting_bankroll=cfg.bankroll,
            daily_stake_limit_fraction=cfg.daily_stake_limit_fraction,
            max_open_bets=cfg.max_open_bets,
            max_open_exposure_fraction=cfg.max_open_exposure_fraction,
            max_bets_per_day=cfg.max_bets_per_day,
            stop_loss_fraction=cfg.stop_loss_fraction,
            min_bankroll_fraction=cfg.min_bankroll_fraction,
        ), self.store)
        # Compound the working bankroll with realised P&L from prior runs.
        if cfg.compound_bankroll:
            self.refresh_bankroll()
        # Latest matched boards, kept so CLV can be captured at kickoff.
        self._last_boards: List[MarketBoard] = []
        # A single Betfair session shared between the price source and executor.
        self._betfair: Optional[BetfairClient] = None
        # Persistent executor reused across a continuous loop.
        self._executor: Optional[Executor] = None

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

    # -- source of truth (fair probabilities) -----------------------------
    def _pinnacle_lines_for_sport(self, sport: str) -> List[FairLine]:
        src = self.cfg.pinnacle_source
        try:
            if src == "sample":
                return sample_pinnacle_lines(sport)
            if src == "the_odds_api":
                return pinnacle_lines_via_odds_api(
                    api_key=self.cfg.odds_api_key or "", sport_key=sport,
                    regions=self.cfg.regions, devig_method=self.cfg.devig_method,
                )
            if src == "direct":
                client = PinnacleClient(self.cfg.pinnacle_username or "",
                                        self.cfg.pinnacle_password or "")
                return client.fair_lines(sport, self.cfg.devig_method)
            raise ValueError(f"unknown pinnacle_source {src!r}")
        except Exception as exc:
            log.error("pinnacle fetch failed for %s: %s", sport, exc)
            return []

    def _consensus_lines_for_sport(self, sport: str, method: str) -> List[FairLine]:
        alpha = {r: self.cfg.consensus_alpha for r in ("home", "draw", "away")}
        try:
            halflife = self.cfg.consensus_recency_halflife_seconds
            if self.cfg.pinnacle_source == "sample":
                return consensus_lines_from_boards(
                    sample_multibook_boards(sport), method=method,
                    book_weights=self.cfg.book_weights,
                    devig_method=self.cfg.devig_method, alpha=alpha,
                    min_books=self.cfg.consensus_min_books,
                    recency_halflife=halflife)
            return consensus_lines_via_odds_api(
                api_key=self.cfg.odds_api_key or "", sport_key=sport,
                regions=self.cfg.regions, method=method,
                book_weights=self.cfg.book_weights,
                devig_method=self.cfg.devig_method, alpha=alpha,
                min_books=self.cfg.consensus_min_books,
                recency_halflife=halflife)
        except Exception as exc:
            log.error("consensus fetch failed for %s: %s", sport, exc)
            return []

    def _fair_lines_for_sport(self, sport: str) -> List[FairLine]:
        model = self.cfg.truth_model
        if model == "pinnacle":
            return self._pinnacle_lines_for_sport(sport)
        if model == "weighted":
            return self._consensus_lines_for_sport(sport, "weighted")
        if model == "consensus":
            return self._consensus_lines_for_sport(sport, "kaunitz")
        if model == "blend":
            return _blend(self._pinnacle_lines_for_sport(sport),
                          self._consensus_lines_for_sport(sport, "weighted"))
        raise ValueError(f"unknown truth_model {model!r}")

    def _fair_lines(self) -> List[FairLine]:
        sports = self.cfg.pinnacle_sports
        if len(sports) <= 1:
            lines = self._fair_lines_for_sport(sports[0]) if sports else []
        else:
            # Fetch sports concurrently to cut total latency near kickoff.
            lines = []
            with ThreadPoolExecutor(max_workers=min(8, len(sports))) as pool:
                for res in pool.map(self._fair_lines_for_sport, sports):
                    lines.extend(res)
        return self._drop_stale(lines)

    def _drop_stale(self, lines: List[FairLine]) -> List[FairLine]:
        """Discard fair lines older than max_line_age_seconds, so we never bet a
        stale price. Lines without a timestamp are kept (can't judge)."""
        max_age = self.cfg.max_line_age_seconds
        if max_age <= 0:
            return lines
        import datetime as _dt
        now = _dt.datetime.now(_dt.timezone.utc)
        fresh = []
        for fl in lines:
            if not fl.last_update:
                fresh.append(fl)
                continue
            try:
                ts = _dt.datetime.fromisoformat(fl.last_update.replace("Z", "+00:00"))
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=_dt.timezone.utc)
                if (now - ts).total_seconds() <= max_age:
                    fresh.append(fl)
            except (ValueError, TypeError):
                fresh.append(fl)
        if len(fresh) < len(lines):
            log.info("dropped %d stale line(s)", len(lines) - len(fresh))
        return fresh

    # -- venue source: Betfair --------------------------------------------
    def _venue_quotes(self) -> List[VenueQuote]:
        if self.cfg.venue_source == "sample":
            return sample_betfair_quotes()
        if self.cfg.venue_source != "betfair":
            raise ValueError(f"unknown venue_source {self.cfg.venue_source!r}")

        types = self.cfg.betfair_event_types or [self.cfg.betfair_event_type]
        quotes: List[VenueQuote] = []
        for sport in types:
            event_type = EVENT_TYPE_IDS.get(sport)
            if not event_type:
                log.error("unknown betfair_event_type %r — skipping", sport)
                continue
            try:
                quotes.extend(self._betfair_client().list_match_odds(
                    event_type_id=event_type,
                    competition_ids=self.cfg.betfair_competition_ids or None,
                    market_start_within_hours=self.cfg.betfair_market_start_within_hours,
                ))
            except Exception as exc:
                log.error("betfair price fetch failed for %s: %s", sport, exc)
        return quotes

    # -- board construction ------------------------------------------------
    def _boards(self) -> List[MarketBoard]:
        if self.cfg.mode == "pinnacle_betfair":
            # Fetch the truth source (Pinnacle) and the venue (Betfair) in
            # parallel — they're independent, so this halves fetch latency.
            with ThreadPoolExecutor(max_workers=2) as pool:
                fair_future = pool.submit(self._fair_lines)
                quotes_future = pool.submit(self._venue_quotes)
                fair = fair_future.result()
                quotes = quotes_future.result()
            boards = EventMatcher(
                min_team_score=self.cfg.match_min_team_score,
                start_window_minutes=self.cfg.match_start_window_minutes,
                ambiguity_margin=self.cfg.match_ambiguity_margin,
            ).build_boards(fair, quotes)
            log.info("pinnacle lines=%d, betfair quotes=%d -> %d matched boards",
                     len(fair), len(quotes), len(boards))
            self._last_boards = boards
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

    def executor(self) -> Executor:
        """A persistent executor, built once and reused across a long-running
        loop (avoids re-login churn on the Betfair session)."""
        if self._executor is None:
            self._executor = self._build_executor()
        return self._executor

    # -- identification only ----------------------------------------------
    def evaluate(self) -> List[ValueBet]:
        """Fetch fresh data, detect value and assign stakes. No placement."""
        from .value import ValueDetector
        boards = self._boards()
        bets = ValueDetector(**self.detector_kwargs).detect(boards)
        staked = self.bankroll.assign(bets)
        log.info("%d boards -> %d value bets, %d stakeable",
                 len(boards), len(bets), len(staked))
        return staked

    # Backwards-compatible alias.
    scan = evaluate

    def place_bets(self, bets: List[ValueBet], dedup: bool = True
                   ) -> List[Tuple[ValueBet, PlacementResult]]:
        """Log and place the given bets through the persistent executor. With
        ``dedup`` (the default) it places AT MOST ONE BET PER EVENT — skipping any
        event that already has a placement, in this batch or a previous one."""
        executor = self.executor()
        results: List[Tuple[ValueBet, PlacementResult]] = []
        placed_events = set()
        # Global circuit-breaker check: if a limit is already hit, bet nothing.
        ok, reason = self.risk.status(self.bankroll.bankroll)
        if not ok:
            log.warning("RISK HALT: %s — no bets placed", reason)
            self.notifier.halt(reason)
            return results
        for bet in bets:
            if dedup and (bet.event_id in placed_events
                          or self.store.already_placed_event(bet.event_id)):
                continue
            # Re-check breakers BEFORE EACH bet so the per-day count / stake /
            # exposure caps can't be blown past within a single batch.
            ok, reason = self.risk.status(self.bankroll.bankroll)
            if not ok:
                log.warning("RISK HALT: %s — stopping placement", reason)
                self.notifier.halt(reason)
                break
            # Cap the stake to remaining daily and open-exposure budgets.
            capped = self.risk.cap_stake(bet.stake, self.bankroll.bankroll)
            if capped < self.cfg.min_stake:
                log.info("skipping %s: risk budget exhausted", bet.selection)
                continue
            bet.stake = round(capped, 2)
            self.store.log_value_bet(bet)
            result = executor.place(bet)
            self.store.log_placement(result, bet)
            results.append((bet, result))
            if result.ok:
                placed_events.add(bet.event_id)
                self.notifier.bet_placed(bet, result)
            log.info("%s %s @ %.2f stake %.2f value %+.2f%% exp-CLV %+.2f%% -> %s (%s)",
                     bet.bookmaker, bet.selection, bet.price, bet.stake,
                     bet.edge * 100, bet.exp_clv * 100, result.status, result.message)
        return results

    def fair_price_for(self, event_id: str, selection: str) -> Optional[float]:
        """Latest fair decimal price for a selection, from the most recent
        matched boards. Used to snapshot the closing line for CLV at kickoff."""
        for board in self._last_boards:
            if board.event_id == event_id and board.fair_probs:
                p = board.fair_probs.get(selection)
                if p and p > 0:
                    return 1.0 / p
        return None

    def market_price_for(self, event_id: str, selection: str) -> Optional[float]:
        """Latest venue (Betfair) back price for a selection — used to capture
        the market's OWN closing price for true CLV."""
        for board in self._last_boards:
            if board.event_id != event_id:
                continue
            for book in board.books:
                if book.bookmaker == "betfair":
                    price = book.price_for(selection)
                    if price:
                        return price
        return None

    def guard_unmatched(self) -> int:
        """Cancel resting (unmatched) Betfair orders so a stale limit bet can't be
        'picked off' after the line moves. Live only. Returns count cancelled."""
        if not (self.cfg.executor == "betfair" and self.cfg.live
                and self.cfg.cancel_unmatched_in_play):
            return 0
        try:
            unmatched = self._betfair_client().list_unmatched()
            if unmatched:
                self._betfair_client().cancel_orders()
            return len(unmatched)
        except Exception as exc:
            log.error("guard_unmatched failed: %s", exc)
            return 0

    def auto_settle(self) -> int:
        """Settle placed bets from Betfair cleared orders (live only). Returns
        the number newly settled; also refreshes the live bankroll."""
        if not (self.cfg.executor == "betfair" and self.cfg.live):
            return 0
        try:
            cleared = self._betfair_client().list_cleared_orders()
            n = self.store.settle_from_betfair(cleared)
            if n:
                self.refresh_bankroll()
            return n
        except Exception as exc:
            log.error("auto-settle failed: %s", exc)
            return 0

    def refresh_bankroll(self) -> float:
        """Update the working bankroll to starting bank + realised profit, so
        Kelly stakes compound on actual results."""
        bank = self.cfg.bankroll + self.store.realised_profit()
        self.bankroll.bankroll = max(0.01, bank)
        return self.bankroll.bankroll

    # -- identify + place + log (one-shot) --------------------------------
    def run(self) -> List[Tuple[ValueBet, PlacementResult]]:
        return self.place_bets(self.evaluate())

    def keep_alive(self) -> None:
        if self._betfair is not None:
            self._betfair.keep_alive()

    def close(self) -> None:
        if self._executor is not None:
            try:
                self._executor.close()
            except Exception:
                pass
            self._executor = None
        if self._betfair is not None:
            self._betfair.close()
        self.store.close()
