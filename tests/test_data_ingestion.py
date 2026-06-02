"""Mock-JSON tests for the data ingestion path (no network).

If these parsers are wrong, the live bot finds no bets — so verify them against
realistic API payloads.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.pinnacle import PinnacleClient
from bot.providers.the_odds_api import TheOddsAPIProvider

ODDS_API_PAYLOAD = [
    {
        "id": "evt1", "sport_key": "soccer_epl",
        "commence_time": "2026-06-02T18:00:00Z",
        "home_team": "Arsenal", "away_team": "Chelsea",
        "bookmakers": [
            {"key": "pinnacle", "title": "Pinnacle", "markets": [
                {"key": "h2h", "last_update": "2026-06-02T17:00:00Z", "outcomes": [
                    {"name": "Arsenal", "price": 1.95},
                    {"name": "Chelsea", "price": 4.20},
                    {"name": "Draw", "price": 3.60}]}]},
            {"key": "bet365", "title": "Bet365", "markets": [
                {"key": "h2h", "last_update": "2026-06-02T17:01:00Z", "outcomes": [
                    {"name": "Arsenal", "price": 2.05},
                    {"name": "Chelsea", "price": 4.00},
                    {"name": "Draw", "price": 3.50}]}]},
        ],
    }
]


class TestOddsApiParse(unittest.TestCase):
    def test_parses_events_books_outcomes(self):
        boards = TheOddsAPIProvider._parse(ODDS_API_PAYLOAD, "soccer_epl", ["h2h"])
        self.assertEqual(len(boards), 1)
        b = boards[0]
        self.assertEqual((b.home_team, b.away_team), ("Arsenal", "Chelsea"))
        self.assertEqual(b.event_id, "evt1")
        self.assertEqual({bk.bookmaker for bk in b.books}, {"pinnacle", "bet365"})
        pin = next(bk for bk in b.books if bk.bookmaker == "pinnacle")
        self.assertEqual(pin.price_for("Arsenal"), 1.95)
        self.assertEqual(pin.last_update, "2026-06-02T17:00:00Z")

    def test_skips_missing_market(self):
        boards = TheOddsAPIProvider._parse(ODDS_API_PAYLOAD, "soccer_epl", ["totals"])
        self.assertEqual(boards, [])

    def test_pinnacle_via_odds_api_devigs(self):
        # Reuse the parser, then the de-vig path used by the consensus/pinnacle.
        provider = TheOddsAPIProvider(api_key="x")
        boards = provider._parse(ODDS_API_PAYLOAD, "soccer_epl", ["h2h"])
        from bot.consensus import consensus_lines_from_boards
        fl = consensus_lines_from_boards(boards, method="weighted", min_books=2)[0]
        self.assertAlmostEqual(sum(fl.probs.values()), 1.0, places=6)
        self.assertGreater(fl.probs["Arsenal"], fl.probs["Chelsea"])


FIXTURES = {"league": [{"events": [
    {"id": 101, "home": "Arsenal", "away": "Chelsea", "starts": "2026-06-02T18:00:00Z"},
    {"id": 102, "home": "Liverpool", "away": "Everton", "starts": "2026-06-02T20:00:00Z"},
]}]}
ODDS = {"leagues": [{"events": [
    {"id": 101, "periods": [{"number": 0, "moneyline": {"home": 1.95, "draw": 3.60, "away": 4.20}}]},
    # period number 1 (first half) must be ignored.
    {"id": 102, "periods": [{"number": 1, "moneyline": {"home": 1.5, "draw": 4.0, "away": 7.0}}]},
]}]}


class TestPinnacleJoin(unittest.TestCase):
    def test_join_full_match_only(self):
        lines = PinnacleClient._join(FIXTURES, ODDS, "soccer", "power")
        # Only event 101 has a full-match (period 0) moneyline.
        self.assertEqual(len(lines), 1)
        fl = lines[0]
        self.assertEqual((fl.home_team, fl.away_team), ("Arsenal", "Chelsea"))
        self.assertEqual(set(fl.probs), {"Arsenal", "Draw", "Chelsea"})
        self.assertAlmostEqual(sum(fl.probs.values()), 1.0, places=6)
        self.assertIsNotNone(fl.overround)
        self.assertGreater(fl.overround, 1.0)  # there is a margin

    def test_missing_fixture_skipped(self):
        odds_only = {"leagues": [{"events": [
            {"id": 999, "periods": [{"number": 0,
                                     "moneyline": {"home": 2.0, "draw": 3.4, "away": 3.8}}]}]}]}
        self.assertEqual(PinnacleClient._join(FIXTURES, odds_only, "soccer", "power"), [])


if __name__ == "__main__":
    unittest.main()
