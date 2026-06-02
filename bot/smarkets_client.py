"""Minimal Smarkets HTTP API wrapper + pure price helpers.

Smarkets is the lowest-cost UK exchange (Pro/API tier ~1% commission, no Premium
Charge) and won't ban winners — the best net-yield automatable venue. This wraps
just what the executor needs: session auth, contract lookup, place, cancel.

IMPORTANT: the live request/response shapes here follow the documented v3 API but
are **not validated against the live exchange**. The price/quantity conventions in
particular MUST be checked against https://docs.smarkets.com before going live.
The executor defaults to dry-run; treat live mode as unproven until you confirm a
single tiny order behaves as expected.
"""
from __future__ import annotations

from typing import Optional

SMARKETS_API_ROOT = "https://api.smarkets.com/v3"

# Smarkets expresses price as implied probability in hundredths of a percent:
# 50.00% -> 5000, so decimal_odds = 10000 / price and price = 10000 / decimal_odds.
SMARKETS_PRICE_MIN = 1       # 0.01%
SMARKETS_PRICE_MAX = 9999    # 99.99%


def decimal_to_smarkets_price(decimal_odds: float) -> int:
    """Decimal odds -> Smarkets integer price (hundredths of a percent)."""
    if decimal_odds <= 1.0:
        raise ValueError("decimal odds must be > 1.0")
    price = round(10000.0 / decimal_odds)
    return max(SMARKETS_PRICE_MIN, min(SMARKETS_PRICE_MAX, int(price)))


def smarkets_price_to_decimal(price: int) -> float:
    """Smarkets integer price -> decimal odds."""
    if not (SMARKETS_PRICE_MIN <= price <= SMARKETS_PRICE_MAX):
        raise ValueError("price out of range")
    return round(10000.0 / price, 4)


def build_order_payload(market_id: str, contract_id: str, decimal_odds: float,
                        stake: float, side: str = "buy") -> dict:
    """Build a limit-order body. side 'buy' = back, 'sell' = lay.

    Quantity is the stake expressed in the API's minor units (hundredths of the
    settlement currency, i.e. pennies). VERIFY against live docs before trusting."""
    if side not in ("buy", "sell"):
        raise ValueError("side must be 'buy' (back) or 'sell' (lay)")
    return {
        "market_id": str(market_id),
        "contract_id": str(contract_id),
        "side": side,
        "type": "limit",
        "price": decimal_to_smarkets_price(decimal_odds),
        "quantity": int(round(stake * 100)),  # pennies
    }


def parse_order_response(resp: dict) -> dict:
    """Normalise a Smarkets order response into a small dict the executor uses."""
    order = (resp or {}).get("order") or resp or {}
    return {
        "id": order.get("id") or order.get("order_id"),
        "status": (order.get("state") or order.get("status") or "").lower(),
        "matched_quantity": order.get("total_matched") or order.get("quantity_filled"),
        "avg_price": order.get("average_price_matched") or order.get("avg_price"),
    }


class SmarketsClient:
    """Thin authenticated HTTP client. Lazily imports the HTTP layer."""

    def __init__(self, username: str, password: str, timeout: float = 15.0):
        if not (username and password):
            raise ValueError("Smarkets needs SMARKETS_USERNAME/PASSWORD")
        self._username = username
        self._password = password
        self.timeout = timeout
        self._token: Optional[str] = None

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self._token:
            h["Authorization"] = self._token
        return h

    def login(self) -> str:
        from .http import post_json
        data, _ = post_json(f"{SMARKETS_API_ROOT}/sessions/",
                            json={"username": self._username,
                                  "password": self._password},
                            headers={"Content-Type": "application/json"},
                            timeout=self.timeout)
        self._token = (data or {}).get("token") or (data or {}).get("session_token")
        if not self._token:
            raise RuntimeError("Smarkets login returned no token")
        return self._token

    def place_order(self, payload: dict) -> dict:
        from .http import post_json
        if not self._token:
            self.login()
        data, _ = post_json(f"{SMARKETS_API_ROOT}/orders/", json=payload,
                            headers=self._headers(), timeout=self.timeout)
        return parse_order_response(data)

    def close(self) -> None:
        self._token = None
