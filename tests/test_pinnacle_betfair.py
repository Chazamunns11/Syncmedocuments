import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.betfair_client import nearest_tick
from bot.bot import ValueBettingBot
from bot.config import Config
from bot.matcher import EventMatcher, normalize, similarity
from bot.samples import sample_betfair_quotes, sample_pinnacle_lines
from bot.value import ValueDetector


class TestBetfairLadder(unittest.TestCase):
    def test_valid_ticks(self):
        self.assertEqual(nearest_tick(2.0), 2.0)
        self.assertEqual(nearest_tick(2.024), 2.02)  # step is 0.02 above 2.0
        self.assertEqual(nearest_tick(1.557), 1.56)  # step 0.01 below 2.0
        self.assertEqual(nearest_tick(3.07), 3.05)   # step 0.05 in 3-4
        self.assertEqual(nearest_tick(11.3), 11.5)   # step 0.5 in 10-20
        self.assertEqual(nearest_tick(0.5), 1.01)    # clamps to min
        self.assertEqual(nearest_tick(5000), 1000.0)  # clamps to max


class TestMatcher(unittest.TestCase):
    def test_normalize_strips_noise(self):
        self.assertEqual(normalize("Arsenal FC"), "arsenal")
        # "United" is kept as a distinguishing token; aliases canonicalise.
        self.assertEqual(normalize("Manchester United"), "manchester united")
        self.assertEqual(normalize("Man Utd"), "manchester united")  # alias
        self.assertEqual(normalize("Spurs"), "tottenham")            # alias

    def test_similarity(self):
        self.assertGreater(similarity("Arsenal", "Arsenal FC"), 0.8)
        self.assertGreater(similarity("Man Utd", "Manchester United"), 0.9)  # alias
        self.assertLess(similarity("Arsenal", "Chelsea"), 0.5)

    def test_builds_aligned_boards(self):
        fair = sample_pinnacle_lines()
        quotes = sample_betfair_quotes()
        boards = EventMatcher().build_boards(fair, quotes)
        self.assertEqual(len(boards), 2)
        board = next(b for b in boards if b.home_team == "Arsenal")
        books = {bk.bookmaker for bk in board.books}
        self.assertEqual(books, {"pinnacle", "betfair"})
        bf = next(bk for bk in board.books if bk.bookmaker == "betfair")
        # Betfair outcomes must carry placement ids and align to Pinnacle names.
        self.assertTrue(all(o.selection_id for o in bf.outcomes))
        self.assertIn("Arsenal", [o.name for o in bf.outcomes])
        self.assertIsNotNone(bf.market_id)

    def test_draw_aligns(self):
        boards = EventMatcher().build_boards(sample_pinnacle_lines(),
                                             sample_betfair_quotes())
        board = next(b for b in boards if b.home_team == "Arsenal")
        bf = next(bk for bk in board.books if bk.bookmaker == "betfair")
        self.assertIn("Draw", [o.name for o in bf.outcomes])


class TestCommissionValue(unittest.TestCase):
    def setUp(self):
        self.boards = EventMatcher().build_boards(
            sample_pinnacle_lines(), sample_betfair_quotes())

    def test_value_found_net_of_commission(self):
        det = ValueDetector(reference_books=["pinnacle"], commission=0.05,
                            min_edge=0.01)
        bets = det.detect(self.boards)
        self.assertTrue(bets)
        top = bets[0]
        self.assertEqual(top.bookmaker, "betfair")
        self.assertEqual(top.selection, "Arsenal")
        # Effective price must be below the gross price (commission applied).
        self.assertLess(top.eff_price, top.price)
        self.assertGreater(top.eff_price, 1.0)
        self.assertTrue(top.venue_selection_id)
        self.assertTrue(top.venue_market_id)
        # Edge is computed on the net price, so it's smaller than the gross edge.
        gross_edge = top.price / top.fair_price - 1.0
        self.assertLess(top.edge, gross_edge)

    def test_high_commission_kills_thin_value(self):
        # A punitive 40% commission should wipe out the ~10% gross edge.
        det = ValueDetector(reference_books=["pinnacle"], commission=0.40,
                            min_edge=0.01)
        self.assertEqual(det.detect(self.boards), [])


class TestEndToEndPinnacleBetfair(unittest.TestCase):
    def test_run_paper(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = Config(
                mode="pinnacle_betfair", pinnacle_source="sample",
                venue_source="sample", executor="betfair", live=False,
                betfair_commission=0.05, min_edge=0.01,
                db_path=os.path.join(d, "p.db"), csv_path=os.path.join(d, "p.csv"),
            )
            bot = ValueBettingBot(cfg)
            try:
                results = bot.run()
                self.assertTrue(results, "expected at least one placed paper bet")
                bet, res = results[0]
                self.assertEqual(bet.bookmaker, "betfair")
                self.assertTrue(res.ok)
                self.assertEqual(bot.store.summary()["n"], len(results))
            finally:
                bot.close()


if __name__ == "__main__":
    unittest.main()
