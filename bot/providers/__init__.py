"""Odds providers: turn an upstream source into a list of MarketBoard objects."""
from .base import OddsProvider
from .the_odds_api import TheOddsAPIProvider
from .sample import SampleProvider

__all__ = ["OddsProvider", "TheOddsAPIProvider", "SampleProvider"]
