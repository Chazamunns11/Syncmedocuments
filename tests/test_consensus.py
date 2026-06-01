import os
import statistics
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.bot import ValueBettingBot, _blend
from bot.config import Config
from bot.consensus import (consensus_lines_from_boards, _role, PAPER_ALPHA)
from bot.models import FairLine
from bot.samples import sample_multibook_boards


class TestConsensusWeighted(unittest.TestCase):
    def setUp(self):
        self.boards = sample_multibook_boards()

    def test_weighted_probs_sum_to_one(self):
        lines = consensus_lines_from_boards(
            self.boards, method="weighted",
            book_weights={"pinnacle": 3.0, "_default": 1.0}, min_books=3)
        self.assertEqual(len(lines), 2)
        for fl in lines:
            self.assertAlmostEqual(sum(fl.probs.values()), 1.0, places=6)
            self.assertEqual(fl.source, "weighted")
            self.assertIsNotNone(fl.overround)

    def test_weighting_pulls_toward_sharp_book(self):
        # Pinnacle's Arsenal price (1.95) implies a higher prob than the soft
        # books, so weighting Pinnacle up should raise the consensus prob.
        light = consensus_lines_from_boards(
            self.boards, method="weighted",
            book_weights={"pinnacle": 1.0, "_default": 1.0}, min_books=3)[0]
        heavy = consensus_lines_from_boards(
            self.boards, method="weighted",
            book_weights={"pinnacle": 10.0, "_default": 1.0}, min_books=3)[0]
        self.assertGreater(heavy.probs["Arsenal"], light.probs["Arsenal"])

    def test_min_books_enforced(self):
        # Requiring 5 books when only 3 quote -> no consensus lines.
        lines = consensus_lines_from_boards(self.boards, method="weighted",
                                            min_books=5)
        self.assertEqual(lines, [])


class TestConsensusKaunitz(unittest.TestCase):
    def test_kaunitz_formula(self):
        # Arsenal odds are 1.95/2.05/2.00 -> mean 2.0 -> p_cons 0.5; alpha 0.05.
        boards = sample_multibook_boards()
        lines = consensus_lines_from_boards(
            boards, method="kaunitz",
            alpha={"home": 0.05, "draw": 0.05, "away": 0.05}, min_books=3)
        arsenal = next(l for l in lines if l.home_team == "Arsenal")
        self.assertAlmostEqual(arsenal.probs["Arsenal"], 0.5 - 0.05, places=6)
        # Per-outcome, deliberately not normalised to 1.
        self.assertNotAlmostEqual(sum(arsenal.probs.values()), 1.0, places=2)

    def test_role_mapping(self):
        self.assertEqual(_role("Draw", "Arsenal", "Chelsea"), "draw")
        self.assertEqual(_role("Chelsea", "Arsenal", "Chelsea"), "away")
        self.assertEqual(_role("Arsenal", "Arsenal", "Chelsea"), "home")

    def test_paper_alphas_present(self):
        self.assertAlmostEqual(PAPER_ALPHA["draw"], 0.057)


class TestBlend(unittest.TestCase):
    def test_blend_averages(self):
        p = [FairLine("e", "s", "", "A", "B", "h2h", {"A": 0.6, "B": 0.4},
                      overround=1.05)]
        c = [FairLine("e", "s", "", "A", "B", "h2h", {"A": 0.5, "B": 0.5},
                      source="weighted", overround=1.03)]
        out = _blend(p, c)
        self.assertEqual(len(out), 1)
        self.assertAlmostEqual(out[0].probs["A"], 0.55, places=6)
        self.assertEqual(out[0].source, "blend")


class TestTruthModelEndToEnd(unittest.TestCase):
    def _run(self, truth_model):
        with tempfile.TemporaryDirectory() as d:
            cfg = Config(truth_model=truth_model, pinnacle_source="sample",
                         venue_source="sample", db_path=os.path.join(d, "t.db"),
                         csv_path=None, min_edge=0.01)
            bot = ValueBettingBot(cfg)
            try:
                return bot.evaluate()
            finally:
                bot.close()

    def test_weighted_finds_value(self):
        bets = self._run("weighted")
        self.assertTrue(bets)
        self.assertEqual(bets[0].bookmaker, "betfair")
        self.assertEqual(bets[0].selection, "Arsenal")

    def test_blend_finds_value(self):
        self.assertTrue(self._run("blend"))

    def test_all_models_run_without_error(self):
        for tm in ("weighted", "pinnacle", "consensus", "blend"):
            self._run(tm)  # must not raise


if __name__ == "__main__":
    unittest.main()
