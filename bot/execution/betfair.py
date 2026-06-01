"""Betfair Exchange executor — the real, sanctioned automated-placement path.

Betfair is a betting *exchange* with an official, documented API that permits
automated placement. Crucially for a user banned from the soft books: an exchange
does not ban or limit winners — you bet against other punters and Betfair simply
takes commission on net winnings.

When a ValueBet was identified from Betfair's own market data (the
Pinnacle→Betfair pipeline), it already carries ``venue_market_id`` and
``venue_selection_id``, so this executor places on the exact runner with no
fuzzy matching. (A name-search fallback exists for bets that lack those ids.)

Set ``dry_run=True`` to resolve/validate without sending an order.
"""
from __future__ import annotations

import difflib
from typing import Optional

from ..betfair_client import BetfairClient
from ..models import PlacementResult, ValueBet

_MARKET_TYPE = {"h2h": "MATCH_ODDS"}


def _similar(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


class BetfairExecutor:
    name = "betfair"

    def __init__(
        self,
        username: str = "",
        password: str = "",
        app_key: str = "",
        certs_path: Optional[str] = None,
        persistence: str = "LAPSE",
        min_name_score: float = 0.8,
        dry_run: bool = True,
        client: Optional[BetfairClient] = None,
    ):
        # Reuse a shared session if one is provided (so the price source and the
        # executor share a single login); otherwise build our own.
        self.client = client or BetfairClient(
            username=username, password=password, app_key=app_key,
            certs_path=certs_path,
        )
        self.persistence = persistence
        self.min_name_score = min_name_score
        self.dry_run = dry_run

    # -- fallback name search (only when ids are absent) -------------------
    def _find_ids(self, bet: ValueBet):
        from betfairlightweight import filters

        client = self.client.trading()
        market_type = _MARKET_TYPE.get(bet.market, "MATCH_ODDS")
        text = bet.matchup.replace(" vs ", " ")
        catalogues = client.betting.list_market_catalogue(
            filter=filters.market_filter(
                text_query=text, market_type_codes=[market_type],
            ),
            market_projection=["RUNNER_DESCRIPTION", "EVENT"],
            max_results=10,
        )
        best, best_score, best_runner = None, 0.0, None
        for cat in catalogues:
            for runner in cat.runners:
                score = _similar(runner.runner_name, bet.selection)
                if score > best_score:
                    best, best_score, best_runner = cat, score, runner
        if best is None or best_score < self.min_name_score:
            return None, None, best_score
        return best.market_id, str(best_runner.selection_id), best_score

    # -- placement ---------------------------------------------------------
    def place(self, bet: ValueBet) -> PlacementResult:
        market_id = bet.venue_market_id
        selection_id = bet.venue_selection_id
        score = 1.0

        if not (market_id and selection_id):
            try:
                market_id, selection_id, score = self._find_ids(bet)
            except Exception as exc:
                return self._err(bet, f"catalogue lookup failed: {exc}")
            if market_id is None:
                return PlacementResult(
                    bet_key=bet.key, executor=self.name, status="REJECTED",
                    requested_price=bet.price, requested_stake=bet.stake,
                    message=f"no Betfair runner matched (best score {score:.2f})",
                )

        ref = f"{market_id}:{selection_id}"
        if self.dry_run:
            return PlacementResult(
                bet_key=bet.key, executor=self.name, status="DRY_RUN",
                requested_price=bet.price, requested_stake=bet.stake,
                external_ref=ref,
                message=f"resolved runner (score {score:.2f}); dry_run, not sent",
            )

        try:
            report = self.client.place_back(
                market_id=market_id, selection_id=selection_id,
                price=bet.price, size=bet.stake, persistence=self.persistence,
            )
        except Exception as exc:
            return self._err(bet, f"place_orders failed: {exc}", ref)

        instr = (report.place_instruction_reports or [None])[0]
        if report.status == "SUCCESS" and instr is not None:
            matched_size = getattr(instr, "size_matched", None)
            avg_price = getattr(instr, "average_price_matched", None) or None
            status = "MATCHED" if matched_size else "PLACED"
            return PlacementResult(
                bet_key=bet.key, executor=self.name, status=status,
                requested_price=bet.price, requested_stake=bet.stake,
                matched_price=avg_price, matched_stake=matched_size,
                external_ref=getattr(instr, "bet_id", None) or ref,
                message=f"betfair status={report.status}",
            )
        return PlacementResult(
            bet_key=bet.key, executor=self.name, status="REJECTED",
            requested_price=bet.price, requested_stake=bet.stake,
            external_ref=ref,
            message=f"betfair status={report.status}; "
                    f"{getattr(instr, 'error_code', '') if instr else ''}",
        )

    def _err(self, bet: ValueBet, msg: str, ref: Optional[str] = None) -> PlacementResult:
        return PlacementResult(
            bet_key=bet.key, executor=self.name, status="ERROR",
            requested_price=bet.price, requested_stake=bet.stake,
            external_ref=ref, message=msg,
        )

    def close(self) -> None:
        self.client.close()
