import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.execution.paper import PaperExecutor
from bot.models import ValueBet
from bot.store import BetStore


def _bet(**kw):
    base = dict(event_id="e", sport_key="s", commence_time="", matchup="A vs B",
                market="h2h", selection="A", bookmaker="betfair", price=2.20,
                fair_prob=0.5, fair_price=2.0, edge=0.05, ev=0.05, kelly_fraction=0.1)
    base.update(kw)
    return ValueBet(**base)


class _ClearedOrder:
    def __init__(self, bet_id, profit):
        self.bet_id = bet_id
        self.profit = profit


class TestTrueCLV(unittest.TestCase):
    def test_market_clv_recorded(self):
        with tempfile.TemporaryDirectory() as d:
            store = BetStore(db_path=os.path.join(d, "c.db"), csv_path=None)
            bet = _bet()
            res = PaperExecutor(seed=1).place(bet)  # matched at 2.20
            store.log_placement(res, bet)
            # Closing fair 2.10, market (Betfair) closed at 2.05.
            store.record_closing(res.external_ref, 2.10, closing_market_price=2.05)
            s = store.summary()
            self.assertEqual(s["clv_n"], 1)
            self.assertEqual(s["clv_mkt_n"], 1)
            # 2.20/2.05 - 1 > 0 -> beat the market close.
            self.assertGreater(s["avg_clv_market"], 0)
            self.assertEqual(s["clv_mkt_beat"], 1)
            store.close()


class TestAutoSettle(unittest.TestCase):
    def test_settle_from_betfair_cleared(self):
        with tempfile.TemporaryDirectory() as d:
            store = BetStore(db_path=os.path.join(d, "c.db"), csv_path=None)
            bet = _bet()
            res = PaperExecutor(seed=2).place(bet)
            # Force a known external_ref so we can match the cleared order.
            res.external_ref = "BET123"
            store.log_placement(res, bet)
            n = store.settle_from_betfair([_ClearedOrder("BET123", profit=14.0)])
            self.assertEqual(n, 1)
            self.assertEqual(store.realised_profit(), 14.0)
            s = store.summary()
            self.assertEqual(s["won"], 1)
            store.close()

    def test_settle_handles_loss_and_void(self):
        with tempfile.TemporaryDirectory() as d:
            store = BetStore(db_path=os.path.join(d, "c.db"), csv_path=None)
            for ref, profit in [("L1", -10.0), ("V1", 0.0)]:
                bet = _bet()
                res = PaperExecutor(seed=3).place(bet)
                res.external_ref = ref
                store.log_placement(res, bet)
            store.settle_from_betfair([_ClearedOrder("L1", -10.0),
                                       _ClearedOrder("V1", 0.0)])
            s = store.summary()
            self.assertEqual(s["lost"], 1)
            self.assertEqual(store.realised_profit(), -10.0)
            store.close()


if __name__ == "__main__":
    unittest.main()
