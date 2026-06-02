"""Notifications for unattended running.

Posts short messages to a webhook (Slack/Discord/any JSON ``{"text": ...}``
endpoint) when bets are placed, a circuit breaker halts betting, or on demand.
Failures here NEVER affect betting — every send is best-effort and swallowed.

Configure with ``notify_webhook_url`` (or the NOTIFY_WEBHOOK_URL env var).
"""
from __future__ import annotations

import logging
from typing import Callable, Optional

log = logging.getLogger("value_bot.notify")


class Notifier:
    def __init__(self, webhook_url: Optional[str] = None,
                 on_bets: bool = True, on_halt: bool = True,
                 poster: Optional[Callable[[str, dict], None]] = None):
        self.webhook_url = webhook_url
        self.on_bets = on_bets
        self.on_halt = on_halt
        # Injectable for testing; defaults to a retrying HTTP POST.
        self._poster = poster or self._default_poster

    @property
    def enabled(self) -> bool:
        return bool(self.webhook_url)

    def _default_poster(self, url: str, payload: dict) -> None:
        from .http import request
        request("POST", url, json=payload, retries=2, backoff=0.5,
                timeout=10.0)

    def send(self, text: str) -> bool:
        """Best-effort post of a plain-text message. Returns True if sent."""
        if not self.webhook_url:
            return False
        try:
            self._poster(self.webhook_url, {"text": text})
            return True
        except Exception as exc:  # never let notifications break the bot
            log.warning("notification failed: %s", exc)
            return False

    # -- events ------------------------------------------------------------
    def bet_placed(self, bet, result) -> None:
        if not (self.on_bets and self.enabled):
            return
        self.send(
            f":moneybag: {result.status} {bet.selection} @ {bet.price:.2f} "
            f"stake {bet.stake:.2f} | {bet.matchup} | value {bet.edge*100:+.2f}% "
            f"exp-CLV {bet.exp_clv*100:+.2f}% [{result.external_ref or '-'}]")

    def halt(self, reason: str) -> None:
        if not (self.on_halt and self.enabled):
            return
        self.send(f":octagonal_sign: RISK HALT — betting paused: {reason}")

    def summary(self, text: str) -> None:
        if self.enabled:
            self.send(f":bar_chart: {text}")
