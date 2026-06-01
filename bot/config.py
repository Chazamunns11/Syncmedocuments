"""Configuration loading.

Config is layered: built-in defaults < config.yaml < environment variables.
Secrets (API keys, Betfair credentials) should come from the environment, never
from a committed file.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field, fields
from typing import List, Optional


@dataclass
class Config:
    # --- what to scan ---
    sports: List[str] = field(default_factory=lambda: ["soccer_epl"])
    markets: List[str] = field(default_factory=lambda: ["h2h"])
    provider: str = "sample"            # "sample" | "the_odds_api"
    regions: str = "uk,eu"

    # --- value detection ---
    reference_books: List[str] = field(default_factory=lambda: ["pinnacle"])
    devig_method: str = "multiplicative"  # multiplicative | additive | shin
    min_edge: float = 0.02
    min_price: float = 1.30
    max_price: float = 15.0

    # --- staking / bankroll ---
    bankroll: float = 1000.0
    kelly_multiplier: float = 0.25
    max_fraction_per_bet: float = 0.02
    min_stake: float = 1.0
    max_stake: float = 100.0
    max_total_exposure_fraction: float = 0.10

    # --- execution ---
    executor: str = "paper"            # "paper" | "betfair"
    live: bool = False                 # MUST be True to place real bets
    paper_slippage: float = 0.0
    paper_fill_probability: float = 1.0
    betfair_dry_run: bool = True

    # --- storage ---
    db_path: str = "bets.db"
    csv_path: str = "bets.csv"

    # --- secrets (env only) ---
    odds_api_key: Optional[str] = None
    betfair_username: Optional[str] = None
    betfair_password: Optional[str] = None
    betfair_app_key: Optional[str] = None
    betfair_certs_path: Optional[str] = None

    @classmethod
    def load(cls, path: Optional[str] = "config.yaml") -> "Config":
        data = {}
        if path and os.path.exists(path):
            try:
                import yaml
                with open(path) as fh:
                    data = yaml.safe_load(fh) or {}
            except ImportError:
                # PyYAML not installed: proceed with defaults + env.
                data = {}
        known = {f.name for f in fields(cls)}
        clean = {k: v for k, v in data.items() if k in known}
        cfg = cls(**clean)
        cfg._apply_env()
        return cfg

    def _apply_env(self) -> None:
        self.odds_api_key = os.getenv("ODDS_API_KEY", self.odds_api_key)
        self.betfair_username = os.getenv("BETFAIR_USERNAME", self.betfair_username)
        self.betfair_password = os.getenv("BETFAIR_PASSWORD", self.betfair_password)
        self.betfair_app_key = os.getenv("BETFAIR_APP_KEY", self.betfair_app_key)
        self.betfair_certs_path = os.getenv("BETFAIR_CERTS_PATH", self.betfair_certs_path)
        # Allow a hard env override for the live switch (belt-and-braces safety).
        if os.getenv("BETTING_LIVE", "").lower() in {"1", "true", "yes"}:
            self.live = True
