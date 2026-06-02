import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.validate import assess_clv
from bot.store import BetStore


class TestAssessCLV(unittest.TestCase):
    def test_empty_collects(self):
        v = assess_clv([], min_n=100)
        self.assertEqual(v.verdict, "COLLECT")
        self.assertEqual(v.n, 0)

    def test_too_few_collects(self):
        v = assess_clv([0.02] * 10, min_n=100)
        self.assertEqual(v.verdict, "COLLECT")
        self.assertEqual(v.n, 10)

    def test_clear_positive_edge_is_go(self):
        # mean +2%, tight spread, enough bets -> CI excludes zero.
        samples = [0.03, 0.01] * 60  # n=120, mean 0.02
        v = assess_clv(samples, min_n=100)
        self.assertEqual(v.verdict, "GO")
        self.assertGreater(v.ci_low, 0)
        self.assertAlmostEqual(v.mean, 0.02, places=6)
        self.assertAlmostEqual(v.beat_rate, 1.0, places=6)

    def test_negative_edge_is_nogo(self):
        v = assess_clv([-0.01, -0.03] * 60, min_n=100)
        self.assertEqual(v.verdict, "NO-GO")
        self.assertLess(v.mean, 0)

    def test_positive_but_noisy_collects_with_target(self):
        # mean +1% but huge spread -> not significant; needs more bets.
        samples = ([0.10] * 50) + ([-0.08] * 50)  # n=100, mean +0.01, large sd
        v = assess_clv(samples, min_n=100)
        self.assertEqual(v.verdict, "COLLECT")
        self.assertLessEqual(v.ci_low, 0)
        self.assertGreater(v.bets_needed, 0)


class TestStoreCLVSamples(unittest.TestCase):
    def test_clv_samples_pulls_non_null(self):
        d = tempfile.mkdtemp()
        store = BetStore(db_path=os.path.join(d, "s.db"), csv_path=None)
        store._conn.execute(
            "INSERT INTO placements (status, clv_market, clv) "
            "VALUES ('DRY_RUN', 0.012, 0.02), ('DRY_RUN', -0.005, 0.01), "
            "('DRY_RUN', NULL, NULL)")
        store._conn.commit()
        mkt = store.clv_samples(market=True)
        mdl = store.clv_samples(market=False)
        self.assertEqual(sorted(mkt), [-0.005, 0.012])
        self.assertEqual(sorted(mdl), [0.01, 0.02])
        store.close()


if __name__ == "__main__":
    unittest.main()
