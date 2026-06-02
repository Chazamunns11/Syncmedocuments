import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.execution.smarkets import SmarketsExecutor
from bot.models import ValueBet
from bot.smarkets_client import (build_order_payload, decimal_to_smarkets_price,
                                 parse_order_response, smarkets_price_to_decimal)


def _bet(**kw):
    base = dict(event_id="e", sport_key="s", commence_time="", matchup="A vs B",
                market="h2h", selection="A", bookmaker="smarkets", price=2.5,
                fair_prob=0.42, fair_price=2.38, edge=0.05, ev=0.05,
                kelly_fraction=0.1, stake=10.0)
    base.update(kw)
    return ValueBet(**base)


class TestPriceMath(unittest.TestCase):
    def test_decimal_to_price(self):
        self.assertEqual(decimal_to_smarkets_price(2.0), 5000)   # 50.00%
        self.assertEqual(decimal_to_smarkets_price(4.0), 2500)   # 25.00%
        self.assertEqual(decimal_to_smarkets_price(1.25), 8000)  # 80.00%

    def test_round_trip(self):
        for odds in (1.5, 2.0, 3.4, 5.0, 11.0):
            p = decimal_to_smarkets_price(odds)
            self.assertAlmostEqual(smarkets_price_to_decimal(p), odds, places=1)

    def test_clamped_and_validated(self):
        self.assertEqual(decimal_to_smarkets_price(100000.0), 1)   # clamps to min
        with self.assertRaises(ValueError):
            decimal_to_smarkets_price(1.0)

    def test_order_payload(self):
        p = build_order_payload("m1", "c9", 2.0, 10.0, side="buy")
        self.assertEqual(p["market_id"], "m1")
        self.assertEqual(p["contract_id"], "c9")
        self.assertEqual(p["side"], "buy")
        self.assertEqual(p["price"], 5000)
        self.assertEqual(p["quantity"], 1000)   # £10 -> 1000 pennies
        with self.assertRaises(ValueError):
            build_order_payload("m", "c", 2.0, 10.0, side="back")  # invalid side

    def test_parse_response(self):
        out = parse_order_response({"order": {"id": 42, "state": "filled",
                                              "average_price_matched": 5000}})
        self.assertEqual(out["id"], 42)
        self.assertEqual(out["status"], "filled")


class TestExecutorDryRun(unittest.TestCase):
    def test_dry_run_places_nothing_and_logs_order(self):
        ex = SmarketsExecutor(dry_run=True)
        res = ex.place(_bet(venue_market_id="m1", venue_selection_id="c9"))
        self.assertEqual(res.status, "DRY_RUN")
        self.assertIn("would place", res.message)
        self.assertTrue(res.external_ref.startswith("smk-dry-"))

    def test_no_ids_falls_back_to_dry_run(self):
        ex = SmarketsExecutor(dry_run=False)  # but no resolved ids -> safe DRY_RUN
        res = ex.place(_bet())
        self.assertEqual(res.status, "DRY_RUN")
        self.assertIn("no resolved market/contract id", res.message)


if __name__ == "__main__":
    unittest.main()
