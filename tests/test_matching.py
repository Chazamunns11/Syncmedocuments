import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.aliases import normalize, similarity
from bot.matcher import EventMatcher
from bot.models import FairLine, VenueQuote


class TestAliases(unittest.TestCase):
    def test_alias_equivalence(self):
        for a, b in [("Man Utd", "Manchester United"), ("Spurs", "Tottenham"),
                     ("Inter", "Internazionale"), ("PSG", "Paris Saint-Germain"),
                     ("Wolves", "Wolverhampton Wanderers")]:
            self.assertGreater(similarity(a, b), 0.9, f"{a} ~ {b}")

    def test_accents_and_punctuation(self):
        self.assertEqual(normalize("Atlético Madrid"), normalize("Atletico Madrid"))
        self.assertGreater(similarity("Bayern München", "Bayern Munich"), 0.9)

    def test_distinct_teams_low(self):
        self.assertLess(similarity("Arsenal", "Aston Villa"), 0.6)
        self.assertLess(similarity("Real Madrid", "Real Sociedad"), 0.8)

    def test_order_independent(self):
        self.assertGreater(similarity("Brighton Hove Albion", "Albion Brighton"), 0.8)


def _fl(key, home, away, when="2026-06-02T18:00:00+00:00"):
    return FairLine(key, "soccer_epl", when, home, away, "h2h",
                    {home: 0.5, "Draw": 0.27, away: 0.23}, overround=1.05)


def _quotes(home, away, when="2026-06-02T18:00:00+00:00", mid="1.1"):
    return [
        VenueQuote("betfair", mid, "1", home, 2.2, 300, f"{home} v {away}",
                   home, away, when, "h2h"),
        VenueQuote("betfair", mid, "2", away, 4.0, 100, f"{home} v {away}",
                   home, away, when, "h2h"),
        VenueQuote("betfair", mid, "3", "The Draw", 3.6, 200, f"{home} v {away}",
                   home, away, when, "h2h"),
    ]


class TestMatcher(unittest.TestCase):
    def test_matches_via_alias(self):
        # Pinnacle says "Manchester United", Betfair says "Man Utd".
        fair = [_fl("e1", "Manchester United", "Liverpool")]
        quotes = _quotes("Man Utd", "Liverpool")
        boards = EventMatcher().build_boards(fair, quotes)
        self.assertEqual(len(boards), 1)

    def test_rejects_wrong_game(self):
        # Only an unrelated event exists -> must NOT match.
        fair = [_fl("e1", "Real Madrid", "Barcelona")]
        quotes = _quotes("Arsenal", "Chelsea")
        self.assertEqual(EventMatcher().build_boards(fair, quotes), [])

    def test_orientation_swap_ok(self):
        fair = [_fl("e1", "Arsenal", "Chelsea")]
        quotes = _quotes("Chelsea", "Arsenal")  # listed away/home swapped
        self.assertEqual(len(EventMatcher().build_boards(fair, quotes)), 1)

    def test_ambiguous_match_skipped(self):
        # Two fair lines for the same teams (different keys) -> ambiguous -> skip.
        fair = [_fl("e1", "Arsenal", "Chelsea"), _fl("e2", "Arsenal", "Chelsea")]
        quotes = _quotes("Arsenal", "Chelsea")
        self.assertEqual(EventMatcher().build_boards(fair, quotes), [])

    def test_time_window_excludes(self):
        fair = [_fl("e1", "Arsenal", "Chelsea", "2026-06-02T18:00:00+00:00")]
        quotes = _quotes("Arsenal", "Chelsea", "2026-06-03T18:00:00+00:00")  # +24h
        self.assertEqual(EventMatcher(start_window_minutes=90)
                         .build_boards(fair, quotes), [])


if __name__ == "__main__":
    unittest.main()
