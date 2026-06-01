import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.value import ValueDetector, kelly_fraction, expected_value
from bot.bankroll import BankrollManager
from bot.providers.sample import SampleProvider


class TestKelly(unittest.TestCase):
    def test_no_edge_is_zero(self):
        # fair coin at fair odds -> no edge -> zero stake
        self.assertAlmostEqual(kelly_fraction(0.5, 2.0), 0.0, places=9)

    def test_positive_edge(self):
        # p=0.5 at 2.20 -> b=1.2, f=(1.2*0.5-0.5)/1.2 = 0.0833...
        self.assertAlmostEqual(kelly_fraction(0.5, 2.2), 0.1 / 1.2, places=6)

    def test_negative_edge_clamped(self):
        self.assertEqual(kelly_fraction(0.4, 2.0), 0.0)

    def test_expected_value(self):
        self.assertAlmostEqual(expected_value(0.5, 2.2), 0.10, places=9)
        self.assertAlmostEqual(expected_value(0.5, 2.0), 0.0, places=9)


class TestDetector(unittest.TestCase):
    def setUp(self):
        self.boards = SampleProvider().fetch("soccer_epl", ["h2h"])

    def test_finds_seeded_value_bet(self):
        det = ValueDetector(reference_books=["pinnacle"], min_edge=0.02)
        bets = det.detect(self.boards)
        self.assertTrue(bets, "expected at least one value bet from sample data")
        top = bets[0]
        # The seeded value is softbook offering 2.15 on Arsenal (fair ~2.00).
        self.assertEqual(top.selection, "Arsenal")
        self.assertEqual(top.bookmaker, "softbook")
        self.assertGreater(top.edge, 0.02)
        self.assertGreater(top.ev, 0.0)

    def test_reference_book_excluded(self):
        det = ValueDetector(reference_books=["pinnacle"])
        bets = det.detect(self.boards)
        self.assertTrue(all(b.bookmaker != "pinnacle" for b in bets))

    def test_efficient_market_yields_nothing_extra(self):
        # Event 2 has all books near sharp line; raise threshold so only the
        # genuine value in event 1 survives.
        det = ValueDetector(reference_books=["pinnacle"], min_edge=0.05)
        bets = det.detect(self.boards)
        self.assertTrue(all(b.event_id == "evt_demo_1" for b in bets))


class TestBankroll(unittest.TestCase):
    def test_stakes_assigned_and_capped(self):
        det = ValueDetector(reference_books=["pinnacle"], min_edge=0.02)
        bets = det.detect(SampleProvider().fetch("soccer_epl", ["h2h"]))
        mgr = BankrollManager(bankroll=1000, kelly_multiplier=0.25,
                              max_fraction_per_bet=0.02, min_stake=1.0)
        staked = mgr.assign(bets)
        self.assertTrue(staked)
        for b in staked:
            self.assertGreater(b.stake, 0)
            self.assertLessEqual(b.stake, 0.02 * 1000 + 1e-9)

    def test_total_exposure_cap(self):
        det = ValueDetector(reference_books=["pinnacle"], min_edge=0.0,
                            min_price=1.0)
        bets = det.detect(SampleProvider().fetch("soccer_epl", ["h2h"]))
        mgr = BankrollManager(bankroll=1000, max_total_exposure_fraction=0.01,
                              min_stake=1.0, max_fraction_per_bet=1.0)
        staked = mgr.assign(bets)
        total = sum(b.stake for b in staked)
        self.assertLessEqual(total, 0.01 * 1000 + 1e-6)


if __name__ == "__main__":
    unittest.main()
