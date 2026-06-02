import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.bot import ValueBettingBot
from bot.config import Config
from bot.consensus import consensus_lines_from_boards
from bot.models import BookOdds, MarketBoard, Outcome, VenueQuote
from bot.value import ValueDetector


class TestTwoWayMarket(unittest.TestCase):
    """Tennis etc. are 2-way (no draw) — the consensus + detector must handle it."""

    def _board(self):
        # Three sharp-ish books on a 2-way market.
        return MarketBoard("t1", "tennis", "", "Alcaraz", "Sinner", "h2h", books=[
            BookOdds("pinnacle", "h2h", [Outcome("Alcaraz", 1.80), Outcome("Sinner", 2.10)]),
            BookOdds("b365", "h2h", [Outcome("Alcaraz", 1.78), Outcome("Sinner", 2.05)]),
            BookOdds("wh", "h2h", [Outcome("Alcaraz", 1.82), Outcome("Sinner", 2.08)]),
        ])

    def test_consensus_two_way(self):
        fl = consensus_lines_from_boards([self._board()], method="weighted",
                                         min_books=3)[0]
        self.assertEqual(set(fl.probs), {"Alcaraz", "Sinner"})
        self.assertAlmostEqual(sum(fl.probs.values()), 1.0, places=6)

    def test_value_found_two_way(self):
        board = self._board()
        fl = consensus_lines_from_boards([board], method="weighted", min_books=3)[0]
        # An exchange over-prices Alcaraz vs the consensus.
        fair_price = 1.0 / fl.probs["Alcaraz"]
        board.books = [BookOdds("betfair", "h2h", [
            Outcome("Alcaraz", round(fair_price * 1.06, 2), selection_id="9", size=200),
            Outcome("Sinner", 2.05, selection_id="8", size=200)], market_id="1.9")]
        board.fair_probs = dict(fl.probs)
        board.fair_source = fl.source
        board.overround = fl.overround
        bets = ValueDetector(commission=0.02, min_edge=0.01).detect([board])
        self.assertTrue(bets)
        self.assertEqual(bets[0].selection, "Alcaraz")


class _FakeBC:
    def __init__(self):
        self.types = []

    def list_match_odds(self, event_type_id, competition_ids=None,
                        market_start_within_hours=None):
        self.types.append(event_type_id)
        return [VenueQuote("betfair", f"m{event_type_id}", "1", "X", 2.0, 50,
                           "X v Y", "X", "Y", "", "h2h")]

    def close(self):
        pass


class TestMultiSportVenue(unittest.TestCase):
    def test_fetches_each_event_type(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = Config(venue_source="betfair",
                         betfair_event_types=["soccer", "tennis"],
                         pinnacle_source="sample",
                         db_path=os.path.join(d, "m.db"), csv_path=None)
            bot = ValueBettingBot(cfg)
            bot._betfair = _FakeBC()
            quotes = bot._venue_quotes()
            # soccer=1, tennis=2 both queried.
            self.assertEqual(set(bot._betfair.types), {"1", "2"})
            self.assertEqual(len(quotes), 2)
            bot.close()


if __name__ == "__main__":
    unittest.main()
