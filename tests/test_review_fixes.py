"""Regression tests for bugs found in the high-effort code review."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.consensus import _role, consensus_lines_from_boards
from bot.matcher import EventMatcher
from bot.models import FairLine, VenueQuote


class TestMaxBetsPerDayWithinBatch(unittest.TestCase):
    """max_bets_per_day must hold WITHIN a single place_bets batch, not just
    once per cycle."""
    def test_count_cap_enforced_mid_batch(self):
        from bot.config import Config
        from bot.bot import ValueBettingBot
        from bot.models import ValueBet
        with tempfile.TemporaryDirectory() as d:
            cfg = Config(pinnacle_source="sample", venue_source="sample",
                         bankroll=100000, max_bets_per_day=3, one_bet_per_event=False,
                         max_open_bets=10**6, compound_bankroll=False,
                         daily_stake_limit_fraction=1.0,
                         max_open_exposure_fraction=1.0, max_fraction_per_bet=1.0,
                         db_path=os.path.join(d, "c.db"), csv_path=None)
            bot = ValueBettingBot(cfg)
            # Fabricate 10 distinct-event value bets.
            bets = [ValueBet(event_id=f"e{i}", sport_key="s", commence_time="",
                             matchup="m", market="h2h", selection="A",
                             bookmaker="betfair", price=2.0, fair_prob=0.5,
                             fair_price=2.0, edge=0.05, ev=0.05, kelly_fraction=0.1,
                             stake=5.0) for i in range(10)]
            placed = bot.place_bets(bets, dedup=False)
            ok = [r for _, r in placed if r.ok]
            self.assertLessEqual(len(ok), 3)  # never exceeds the daily cap
            bot.close()


class TestRunnerUniqueness(unittest.TestCase):
    def test_two_runners_to_same_selection_rejected(self):
        # Both Betfair runners are named like the SAME Pinnacle selection.
        fl = FairLine("e", "s", "2026-06-02T18:00:00+00:00", "Manchester United",
                      "Chelsea", "h2h",
                      {"Manchester United": 0.5, "Draw": 0.27, "Chelsea": 0.23},
                      overround=1.05)
        quotes = [
            VenueQuote("betfair", "1.1", "1", "Man Utd", 2.2, 100, "x", "Man Utd",
                       "Man United", "2026-06-02T18:00:00+00:00", "h2h"),
            VenueQuote("betfair", "1.1", "2", "Man United", 4.0, 100, "x", "Man Utd",
                       "Man United", "2026-06-02T18:00:00+00:00", "h2h"),
        ]
        # Both runners alias to "Manchester United" -> collision -> board rejected.
        boards = EventMatcher(min_team_score=0.5).build_boards([fl], quotes)
        for b in boards:
            bf = next((bk for bk in b.books if bk.bookmaker == "betfair"), None)
            if bf:
                names = [o.name for o in bf.outcomes]
                self.assertEqual(len(names), len(set(names)))  # no duplicate sel


class TestRoleRobustness(unittest.TestCase):
    def test_role_tolerates_case_whitespace_alias(self):
        self.assertEqual(_role("Real Madrid ", "Barcelona", "Real Madrid"), "away")
        self.assertEqual(_role("man utd", "Manchester United", "Chelsea"), "home")
        self.assertEqual(_role("The Draw", "A", "B"), "draw")

    def test_kaunitz_applies_alpha_to_correct_side(self):
        from bot.models import BookOdds, MarketBoard, Outcome
        # Away outcome name differs in case from away_team.
        board = MarketBoard("e", "s", "", "Arsenal", "Chelsea", "h2h", books=[
            BookOdds(b, "h2h", [Outcome("Arsenal", 2.0), Outcome("Draw", 3.4),
                                Outcome("chelsea", 3.8)])
            for b in ("pinnacle", "b365", "wh")])
        fl = consensus_lines_from_boards([board], method="kaunitz",
                                         alpha={"home": 0.0, "draw": 0.0, "away": 0.2},
                                         min_books=3)[0]
        # Away alpha (0.2) is large -> "chelsea" prob heavily reduced despite the
        # lowercase mismatch with away_team "Chelsea".
        self.assertLess(fl.probs["chelsea"], 1.0 / 3.8 - 0.1)


if __name__ == "__main__":
    unittest.main()
