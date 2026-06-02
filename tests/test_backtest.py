import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.backtest import (_discover_books, run_backtest, synthetic_rows,
                          format_result, sweep, format_sweep,
                          walk_forward, format_walk_forward)


class TestDiscoverBooks(unittest.TestCase):
    def setUp(self):
        self.row = synthetic_rows(1)[0]

    def test_opening_books_include_soft_vc(self):
        opening = _discover_books(self.row, closing=False)
        self.assertIn("VC", opening)   # VC ends in C but is NOT closing
        self.assertIn("PS", opening)
        self.assertNotIn("PSC", opening)

    def test_closing_books_detected(self):
        closing = _discover_books(self.row, closing=True)
        self.assertIn("PSC", closing)  # PSC = PS + C -> closing
        self.assertNotIn("VC", closing)


class TestBacktest(unittest.TestCase):
    def test_edge_is_profitable_and_positive_clv(self):
        rows = synthetic_rows(n=3000, edge=0.03, seed=11)
        res = run_backtest(rows, method="weighted", min_edge=0.01,
                           flat_stake=10.0)
        self.assertGreater(res.bets, 100)
        self.assertGreater(res.profit, 0)
        self.assertGreater(res.avg_clv, 0)
        self.assertEqual(res.clv_positive_rate, 1.0)  # closing at fair, we beat it
        self.assertEqual(len(res.equity_curve), res.bets)
        self.assertGreaterEqual(res.max_drawdown, 0.0)

    def test_no_edge_makes_few_or_no_bets(self):
        # With zero seeded overlay and a 2% edge requirement, the soft book's tiny
        # noise should rarely clear the bar -> far fewer bets than the edge case.
        edge_rows = synthetic_rows(n=2000, edge=0.03, seed=5)
        flat_rows = synthetic_rows(n=2000, edge=0.0, seed=5)
        edgy = run_backtest(edge_rows, min_edge=0.02, flat_stake=10.0)
        flat = run_backtest(flat_rows, min_edge=0.02, flat_stake=10.0)
        self.assertGreater(edgy.bets, flat.bets)

    def test_commission_reduces_profit(self):
        rows = synthetic_rows(n=3000, edge=0.04, seed=3)
        gross = run_backtest(rows, min_edge=0.01, commission=0.0, flat_stake=10.0)
        net = run_backtest(rows, min_edge=0.01, commission=0.05, flat_stake=10.0)
        self.assertGreater(gross.profit, net.profit)

    def test_format_runs(self):
        res = run_backtest(synthetic_rows(200), flat_stake=5.0)
        self.assertIn("Backtest result", format_result(res))

    def test_edge_buckets_populated(self):
        res = run_backtest(synthetic_rows(2000, edge=0.04), min_edge=0.01,
                           flat_stake=10.0)
        self.assertTrue(res.buckets)
        # Every bucket's bets sum to the total.
        self.assertEqual(sum(b["bets"] for b in res.buckets.values()), res.bets)


class TestSweep(unittest.TestCase):
    def test_sweep_ranks_by_clv(self):
        rows = synthetic_rows(n=1500, edge=0.04, seed=9)
        ranked = sweep(rows, grid={
            "method": ["weighted"], "min_edge": [0.02, 0.04],
            "devig_method": ["power"], "consensus_alpha": [0.05]})
        self.assertTrue(ranked)
        clvs = [r.avg_clv for _, r in ranked if r.avg_clv is not None]
        self.assertEqual(clvs, sorted(clvs, reverse=True))  # best-first
        self.assertIn("sweep", format_sweep(ranked).lower())


class TestWalkForward(unittest.TestCase):
    def test_train_test_split_and_report(self):
        rows = synthetic_rows(n=2000, edge=0.04, seed=21)
        params, train, test = walk_forward(rows, grid={
            "method": ["weighted"], "min_edge": [0.02, 0.04],
            "devig_method": ["power"], "consensus_alpha": [0.05]})
        self.assertIsNotNone(params)
        self.assertGreater(train.bets, 0)
        self.assertGreater(test.bets, 0)
        # The synthetic closing line is fair, so out-of-sample CLV stays positive.
        self.assertGreater(test.avg_clv, 0)
        self.assertIn("out-of-sample", format_walk_forward(params, train, test))

    def test_too_few_rows_raises(self):
        with self.assertRaises(ValueError):
            walk_forward(synthetic_rows(10))


if __name__ == "__main__":
    unittest.main()
