import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.bankroll import BankrollManager
from bot.models import ValueBet, clv_priority_key


def _bet(event, sel, edge, exp_clv, stake=0.0, kelly=0.1):
    return ValueBet(event_id=event, sport_key="s", commence_time="", matchup="m",
                    market="h2h", selection=sel, bookmaker="betfair", price=3.0,
                    fair_prob=0.34, fair_price=2.9, edge=edge, ev=edge,
                    kelly_fraction=kelly, stake=stake, exp_clv=exp_clv)


class TestCLVPriority(unittest.TestCase):
    def test_key_orders_by_clv_then_edge(self):
        a = _bet("e1", "A", edge=0.10, exp_clv=0.01)  # big edge, small CLV
        b = _bet("e2", "B", edge=0.02, exp_clv=0.05)  # small edge, big CLV
        ranked = sorted([a, b], key=clv_priority_key, reverse=True)
        self.assertEqual([x.selection for x in ranked], ["B", "A"])  # CLV wins

    def test_tie_breaks_on_edge(self):
        a = _bet("e1", "A", edge=0.03, exp_clv=0.04)
        b = _bet("e2", "B", edge=0.06, exp_clv=0.04)  # same CLV, bigger edge
        ranked = sorted([a, b], key=clv_priority_key, reverse=True)
        self.assertEqual([x.selection for x in ranked], ["B", "A"])

    def test_scarce_capital_funds_highest_clv_first(self):
        # Exposure budget only covers ~one flat stake; the higher-CLV bet wins it.
        bk = BankrollManager(bankroll=1000.0, flat_stake=60.0, min_stake=1.0,
                      max_stake=100.0, max_total_exposure_fraction=0.06)  # budget 60
        low = _bet("e1", "LOW", edge=0.10, exp_clv=0.01)
        high = _bet("e2", "HIGH", edge=0.02, exp_clv=0.08)
        staked = bk.assign([low, high])
        self.assertEqual(len(staked), 1)
        self.assertEqual(staked[0].selection, "HIGH")  # CLV, not edge, got funded
        self.assertEqual(staked[0].stake, 60.0)


if __name__ == "__main__":
    unittest.main()
