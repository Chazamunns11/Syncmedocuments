"""Smarkets executor — lowest-cost UK exchange venue.

Mirrors the Betfair executor's shape. Defaults to **dry-run**: it builds and logs
the exact order it WOULD place but sends nothing. Live placement requires both
``dry_run=False`` and resolved market/contract ids. As with the Betfair path, the
live API calls are structurally complete but UNVALIDATED against the real exchange
— prove a single tiny order by hand before trusting it. See bot/smarkets_client.py.
"""
from __future__ import annotations

import uuid
from typing import Optional

from ..models import PlacementResult, ValueBet
from ..smarkets_client import SmarketsClient, build_order_payload


class SmarketsExecutor:
    name = "smarkets"

    def __init__(self, client: Optional[SmarketsClient] = None,
                 username: str = "", password: str = "", dry_run: bool = True):
        # Build a client lazily; in dry-run we never need credentials.
        self._client = client
        self._username = username
        self._password = password
        self.dry_run = dry_run

    def client(self) -> SmarketsClient:
        if self._client is None:
            self._client = SmarketsClient(self._username, self._password)
        return self._client

    def place(self, bet: ValueBet) -> PlacementResult:
        # Need the venue ids resolved upstream (matcher/price fetch) to place live.
        market_id = bet.venue_market_id
        contract_id = bet.venue_selection_id
        try:
            payload = build_order_payload(
                market_id or "?", contract_id or "?", bet.price, bet.stake, side="buy")
        except ValueError as exc:
            return self._err(bet, f"bad order: {exc}")

        if self.dry_run or not (market_id and contract_id):
            reason = "dry-run" if self.dry_run else "no resolved market/contract id"
            return PlacementResult(
                bet_key=bet.key, executor=self.name, status="DRY_RUN",
                requested_price=bet.price, requested_stake=bet.stake,
                external_ref=f"smk-dry-{uuid.uuid4().hex[:10]}",
                message=f"would place ({reason}): {payload}",
            )
        try:
            res = self.client().place_order(payload)
        except Exception as exc:
            return self._err(bet, f"place_order failed: {exc}")
        status = "MATCHED" if res.get("status") in ("filled", "matched") else "PLACED"
        return PlacementResult(
            bet_key=bet.key, executor=self.name, status=status,
            requested_price=bet.price, requested_stake=bet.stake,
            matched_price=bet.price, external_ref=str(res.get("id") or ""),
            message=f"smarkets order {res.get('status')}",
        )

    def _err(self, bet: ValueBet, msg: str) -> PlacementResult:
        return PlacementResult(
            bet_key=bet.key, executor=self.name, status="ERROR",
            requested_price=bet.price, requested_stake=bet.stake, message=msg)

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
