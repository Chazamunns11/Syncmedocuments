import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.config import Config
from bot.bot import ValueBettingBot, build_executor
from bot.execution.paper import PaperExecutor
from bot.store import BetStore
from bot.models import ValueBet


class TestPaperExecutor(unittest.TestCase):
    def _bet(self):
        return ValueBet(
            event_id="e", sport_key="s", commence_time="t", matchup="A vs B",
            market="h2h", selection="A", bookmaker="softbook", price=2.10,
            fair_prob=0.5, fair_price=2.0, edge=0.05, ev=0.05,
            kelly_fraction=0.05, stake=10.0,
        )

    def test_paper_fill(self):
        ex = PaperExecutor(seed=1)
        res = ex.place(self._bet())
        self.assertTrue(res.ok)
        self.assertEqual(res.status, "MATCHED")
        self.assertEqual(res.matched_stake, 10.0)
        self.assertTrue(res.external_ref.startswith("paper-"))

    def test_slippage_applied(self):
        ex = PaperExecutor(slippage=0.10, seed=1)
        res = ex.place(self._bet())
        self.assertAlmostEqual(res.matched_price, 2.10 * 0.9, places=4)


class TestStore(unittest.TestCase):
    def test_log_and_settle(self):
        with tempfile.TemporaryDirectory() as d:
            store = BetStore(db_path=os.path.join(d, "t.db"),
                             csv_path=os.path.join(d, "t.csv"))
            bet = ValueBet(
                event_id="e", sport_key="s", commence_time="t", matchup="A vs B",
                market="h2h", selection="A", bookmaker="b", price=2.0,
                fair_prob=0.55, fair_price=1.82, edge=0.1, ev=0.1,
                kelly_fraction=0.1, stake=20.0,
            )
            store.log_value_bet(bet)
            ex = PaperExecutor(seed=2)
            res = ex.place(bet)
            store.log_placement(res)

            profit = store.settle(res.external_ref, "WON")
            self.assertAlmostEqual(profit, 20.0 * (res.matched_price - 1.0), places=6)

            summary = store.summary()
            self.assertEqual(summary["won"], 1)
            self.assertGreater(summary["profit"], 0)
            self.assertTrue(os.path.exists(os.path.join(d, "t.csv")))
            store.close()


class TestSafetyGate(unittest.TestCase):
    def test_betfair_without_live_falls_back_to_paper(self):
        cfg = Config(executor="betfair", live=False)
        ex = build_executor(cfg)
        self.assertIsInstance(ex, PaperExecutor)

    def test_default_executor_is_paper(self):
        cfg = Config()
        self.assertIsInstance(build_executor(cfg), PaperExecutor)


class TestEndToEnd(unittest.TestCase):
    def test_run_pipeline_paper(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = Config(
                provider="sample", executor="paper", live=False,
                db_path=os.path.join(d, "e.db"), csv_path=os.path.join(d, "e.csv"),
                min_edge=0.02,
            )
            bot = ValueBettingBot(cfg)
            try:
                results = bot.run()
                self.assertTrue(results, "pipeline should place at least one paper bet")
                self.assertTrue(all(r.ok for _, r in results))
                self.assertEqual(bot.store.summary()["n"], len(results))
            finally:
                bot.close()


if __name__ == "__main__":
    unittest.main()
