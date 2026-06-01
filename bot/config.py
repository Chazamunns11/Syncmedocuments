"""Configuration loading.

Config is layered: built-in defaults < config.yaml < environment variables.
Secrets (API keys, Betfair credentials) should come from the environment, never
from a committed file.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field, fields
from typing import Dict, List, Optional


@dataclass
class Config:
    # --- pipeline mode ---
    # "pinnacle_betfair": value Betfair Exchange prices against Pinnacle (the
    #   source of truth) and place on Betfair. This is the recommended mode if
    #   you're limited/banned on the soft books.
    # "multi_book": classic cross-bookmaker value scan from a single odds feed.
    mode: str = "pinnacle_betfair"

    # --- what to scan ---
    sports: List[str] = field(default_factory=lambda: ["soccer_epl"])
    markets: List[str] = field(default_factory=lambda: ["h2h"])
    provider: str = "sample"            # multi_book feed: "sample" | "the_odds_api"
    regions: str = "uk,eu"

    # --- source of truth model ---
    # How the fair probability is estimated:
    #   "weighted"  - weighted Power-Method consensus across sharp + soft books
    #                 (practitioner method; the most accurate default)
    #   "pinnacle"  - single sharp book (Pinnacle), de-vigged
    #   "consensus" - Kaunitz et al.: 1/mean(odds) - alpha (bias-corrected)
    #   "blend"     - average of the pinnacle and weighted estimates
    truth_model: str = "weighted"
    # Per-bookmaker weights for the weighted consensus ("_default" applies to any
    # book not listed). Sharp books should be weighted higher.
    book_weights: Dict[str, float] = field(
        default_factory=lambda: {"pinnacle": 3.0, "_default": 1.0})
    consensus_min_books: int = 3        # min bookmakers required for a consensus
    consensus_alpha: float = 0.05       # Kaunitz bias term (single-value form)

    # --- pinnacle (source of truth) ---
    pinnacle_source: str = "sample"     # "sample" | "the_odds_api" | "direct"
    # Pinnacle's own sport key naming differs per source; for the_odds_api use
    # the odds-api sport key (e.g. soccer_epl); for direct use a sport in
    # pinnacle.PINNACLE_SPORT_IDS (e.g. "soccer").
    pinnacle_sports: List[str] = field(default_factory=lambda: ["soccer_epl"])

    # --- betfair (betting venue) ---
    venue_source: str = "sample"        # "sample" | "betfair"
    betfair_event_type: str = "soccer"  # key in betfair_client.EVENT_TYPE_IDS
    betfair_competition_ids: List[str] = field(default_factory=list)
    betfair_commission: float = 0.05    # commission on net winnings (UK base 5%)
    betfair_market_start_within_hours: int = 72

    # --- event matching (pinnacle <-> betfair) ---
    match_min_team_score: float = 0.80   # strict: avoid betting the wrong game
    match_start_window_minutes: int = 90
    match_ambiguity_margin: float = 0.08  # reject if 2nd-best match is this close

    # --- value detection ---
    reference_books: List[str] = field(default_factory=lambda: ["pinnacle"])
    devig_method: str = "power"        # multiplicative | additive | shin | power
    min_edge: float = 0.02
    min_price: float = 1.30
    max_price: float = 15.0
    edge_haircut: float = 0.01         # conservative edge cut for estimation error
    min_liquidity: float = 10.0        # min money available to back at the venue
    max_overround: float = 1.15        # skip Pinnacle markets wider than this booksum
    min_expected_clv: float = 0.0      # only bet when expected CLV exceeds this (>0)
    one_bet_per_event: bool = True     # never place more than one bet on an event

    # --- continuous / near-kickoff scheduling ---
    poll_interval_seconds: float = 60.0     # cadence when nothing is near kickoff
    refresh_interval_seconds: float = 5.0   # cadence when an event is in-window
    place_window_minutes: float = 3.0       # start betting this long before kickoff
    min_seconds_before_start: float = 20.0  # stop betting this close to kickoff

    # --- staking / bankroll ---
    bankroll: float = 1000.0           # your budget / starting bank
    kelly_multiplier: float = 0.20      # 15-20% Kelly is the practitioner range
    flat_stake: Optional[float] = None  # if set, stake this fixed amount per bet
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
    pinnacle_username: Optional[str] = None
    pinnacle_password: Optional[str] = None

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
        self.pinnacle_username = os.getenv("PINNACLE_USERNAME", self.pinnacle_username)
        self.pinnacle_password = os.getenv("PINNACLE_PASSWORD", self.pinnacle_password)
        # Allow a hard env override for the live switch (belt-and-braces safety).
        if os.getenv("BETTING_LIVE", "").lower() in {"1", "true", "yes"}:
            self.live = True
