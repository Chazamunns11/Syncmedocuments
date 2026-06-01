"""Betfair Exchange executor — the real, sanctioned automated-placement path.

Betfair is a betting *exchange* and offers an official, documented REST API for
placing and managing bets. Unlike traditional sportsbooks, automated placement
here is allowed under their developer programme. You need:

  * a Betfair account + funded wallet,
  * an Application Key (https://developer.betfair.com),
  * login credentials (we use the certificate / non-interactive login).

This executor uses ``betfairlightweight`` (pip install betfairlightweight). It is
imported lazily so the rest of the bot never depends on it.

IMPORTANT MATCHING CAVEAT
-------------------------
A ValueBet identified from The Odds API does not carry Betfair market/selection
ids. We therefore look the event up in Betfair's market catalogue by team names
and market type and match the runner by name. Name matching across data sources
is imperfect; review ``min_name_score`` and the logs before trusting live fills.
Set ``dry_run=True`` to resolve ids and price the order *without* sending it.
"""
from __future__ import annotations

import difflib
from typing import Optional

from ..models import PlacementResult, ValueBet

# The Odds API h2h selections are team names / "Draw"; map market keys to
# Betfair market type codes.
_MARKET_TYPE = {
    "h2h": "MATCH_ODDS",
    "totals": "OVER_UNDER_25",
    "spreads": "HANDICAP",
}


def _similar(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


class BetfairExecutor:
    name = "betfair"

    def __init__(
        self,
        username: str,
        password: str,
        app_key: str,
        certs_path: Optional[str] = None,
        persistence: str = "LAPSE",
        min_name_score: float = 0.8,
        dry_run: bool = True,
        locale: str = "en",
    ):
        if not (username and password and app_key):
            raise ValueError("Betfair requires username, password and app_key")
        self.username = username
        self.password = password
        self.app_key = app_key
        self.certs_path = certs_path
        self.persistence = persistence
        self.min_name_score = min_name_score
        self.dry_run = dry_run
        self.locale = locale
        self._client = None

    # -- session -----------------------------------------------------------
    def _trading(self):
        if self._client is not None:
            return self._client
        try:
            import betfairlightweight
        except ImportError as exc:  # pragma: no cover - depends on optional dep
            raise RuntimeError(
                "betfairlightweight is not installed. Run "
                "`pip install betfairlightweight` to use the Betfair executor."
            ) from exc
        client = betfairlightweight.APIClient(
            username=self.username,
            password=self.password,
            app_key=self.app_key,
            certs=self.certs_path,
            locale=self.locale,
        )
        if self.certs_path:
            client.login()
        else:
            client.login_interactive()
        self._client = client
        return client

    # -- catalogue matching ------------------------------------------------
    def _find_market_and_runner(self, bet: ValueBet):
        from betfairlightweight import filters

        client = self._trading()
        market_type = _MARKET_TYPE.get(bet.market, "MATCH_ODDS")
        # bet.matchup is "Home vs Away"; search on both team names as keywords.
        text = bet.matchup.replace(" vs ", " ")
        market_filter = filters.market_filter(
            text_query=text,
            market_type_codes=[market_type],
        )
        catalogues = client.betting.list_market_catalogue(
            filter=market_filter,
            market_projection=["RUNNER_DESCRIPTION", "EVENT"],
            max_results=10,
        )
        best = None
        best_score = 0.0
        best_runner = None
        for cat in catalogues:
            for runner in cat.runners:
                score = _similar(runner.runner_name, bet.selection)
                if score > best_score:
                    best_score = score
                    best = cat
                    best_runner = runner
        if best is None or best_score < self.min_name_score:
            return None, None, best_score
        return best.market_id, best_runner.selection_id, best_score

    # -- placement ---------------------------------------------------------
    def place(self, bet: ValueBet) -> PlacementResult:
        try:
            market_id, selection_id, score = self._find_market_and_runner(bet)
        except Exception as exc:  # network/login/library errors
            return PlacementResult(
                bet_key=bet.key, executor=self.name, status="ERROR",
                requested_price=bet.price, requested_stake=bet.stake,
                message=f"catalogue lookup failed: {exc}",
            )
        if market_id is None:
            return PlacementResult(
                bet_key=bet.key, executor=self.name, status="REJECTED",
                requested_price=bet.price, requested_stake=bet.stake,
                message=f"no Betfair market/runner matched (best score {score:.2f})",
            )

        if self.dry_run:
            return PlacementResult(
                bet_key=bet.key, executor=self.name, status="DRY_RUN",
                requested_price=bet.price, requested_stake=bet.stake,
                external_ref=f"{market_id}:{selection_id}",
                message=f"matched runner (score {score:.2f}); dry_run, not sent",
            )

        from betfairlightweight import filters

        client = self._trading()
        order = filters.limit_order(
            size=round(bet.stake, 2),
            price=bet.price,
            persistence_type=self.persistence,
        )
        instruction = filters.place_instruction(
            order_type="LIMIT",
            selection_id=selection_id,
            side="BACK",
            limit_order=order,
        )
        try:
            report = client.betting.place_orders(
                market_id=market_id, instructions=[instruction]
            )
        except Exception as exc:
            return PlacementResult(
                bet_key=bet.key, executor=self.name, status="ERROR",
                requested_price=bet.price, requested_stake=bet.stake,
                external_ref=f"{market_id}:{selection_id}",
                message=f"place_orders failed: {exc}",
            )

        instr = report.place_instruction_reports[0] if report.place_instruction_reports else None
        if report.status == "SUCCESS" and instr is not None:
            matched_size = getattr(instr, "size_matched", None)
            avg_price = getattr(instr, "average_price_matched", None) or None
            status = "MATCHED" if matched_size else "PLACED"
            return PlacementResult(
                bet_key=bet.key, executor=self.name, status=status,
                requested_price=bet.price, requested_stake=bet.stake,
                matched_price=avg_price, matched_stake=matched_size,
                external_ref=getattr(instr, "bet_id", None),
                message=f"betfair status={report.status}",
            )
        return PlacementResult(
            bet_key=bet.key, executor=self.name, status="REJECTED",
            requested_price=bet.price, requested_stake=bet.stake,
            external_ref=f"{market_id}:{selection_id}",
            message=f"betfair status={report.status}; "
                    f"{getattr(instr, 'error_code', '') if instr else ''}",
        )

    def close(self) -> None:
        if self._client is not None:
            try:
                self._client.logout()
            except Exception:
                pass
            self._client = None
