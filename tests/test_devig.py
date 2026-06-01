import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.devig import devig, booksum, multiplicative, additive, shin


class TestDevig(unittest.TestCase):
    def test_probabilities_sum_to_one(self):
        odds = [1.95, 1.95]
        for method in ("multiplicative", "additive", "shin"):
            probs = devig(odds, method=method)
            self.assertAlmostEqual(sum(probs), 1.0, places=9,
                                   msg=f"{method} did not normalise")

    def test_symmetric_market_is_fifty_fifty(self):
        odds = [1.95, 1.95]
        for method in ("multiplicative", "additive", "shin"):
            probs = devig(odds, method=method)
            self.assertAlmostEqual(probs[0], 0.5, places=6)
            self.assertAlmostEqual(probs[1], 0.5, places=6)

    def test_removes_overround(self):
        odds = [1.95, 1.95]
        self.assertGreater(booksum(odds), 1.0)  # there IS a margin
        probs = multiplicative(odds)
        self.assertAlmostEqual(sum(probs), 1.0, places=9)

    def test_favourite_has_higher_prob(self):
        odds = [1.50, 2.70]  # first is favourite
        probs = devig(odds, "multiplicative")
        self.assertGreater(probs[0], probs[1])

    def test_shin_shifts_toward_longshot(self):
        # Shin attributes margin to insiders -> favourite prob lower than the
        # naive multiplicative estimate, longshot prob higher.
        odds = [1.20, 6.0]
        mult = multiplicative(odds)
        sh = shin(odds)
        self.assertLess(sh[0], mult[0] + 1e-9)
        self.assertGreaterEqual(sh[1], mult[1] - 1e-9)

    def test_three_way_market(self):
        odds = [2.40, 3.30, 3.10]  # home / draw / away
        for method in ("multiplicative", "additive", "shin"):
            probs = devig(odds, method)
            self.assertAlmostEqual(sum(probs), 1.0, places=8)
            self.assertTrue(all(0 < p < 1 for p in probs))

    def test_rejects_bad_odds(self):
        with self.assertRaises(ValueError):
            devig([1.0, 2.0])
        with self.assertRaises(ValueError):
            devig([2.0])

    def test_unknown_method(self):
        with self.assertRaises(ValueError):
            devig([1.9, 1.9], method="nope")


if __name__ == "__main__":
    unittest.main()
