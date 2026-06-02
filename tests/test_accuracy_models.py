import datetime as dt
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.consensus import _recency_weight, consensus_lines_from_boards
from bot.devig import devig, ensemble, multiplicative, shin, power
from bot.models import BookOdds, MarketBoard, Outcome


class TestEnsembleDevig(unittest.TestCase):
    def test_sums_to_one(self):
        for odds in ([1.95, 1.95], [2.4, 3.3, 3.1], [1.2, 6.0]):
            self.assertAlmostEqual(sum(ensemble(odds)), 1.0, places=9)

    def test_between_component_methods(self):
        odds = [1.2, 6.0]
        e = ensemble(odds)[0]
        comps = sorted([multiplicative(odds)[0], shin(odds)[0], power(odds)[0]])
        self.assertGreaterEqual(e, comps[0] - 1e-9)
        self.assertLessEqual(e, comps[-1] + 1e-9)

    def test_dispatch(self):
        self.assertAlmostEqual(sum(devig([2.0, 2.0], "ensemble")), 1.0, places=9)


class TestRecencyWeight(unittest.TestCase):
    def _iso(self, secs_ago):
        return (dt.datetime.now(dt.timezone.utc)
                - dt.timedelta(seconds=secs_ago)).isoformat()

    def test_disabled_returns_one(self):
        self.assertEqual(_recency_weight(self._iso(1000), 0.0), 1.0)
        self.assertEqual(_recency_weight(None, 60.0), 1.0)

    def test_decays_with_age(self):
        fresh = _recency_weight(self._iso(0), 60.0)
        old = _recency_weight(self._iso(120), 60.0)  # 2 half-lives
        self.assertGreater(fresh, old)
        self.assertAlmostEqual(old, 0.25, delta=0.05)  # ~0.5^2

    def test_recency_shifts_consensus(self):
        # Two books disagree; the fresher one should pull the consensus.
        now = dt.datetime.now(dt.timezone.utc)
        recent = (now - dt.timedelta(seconds=1)).isoformat()
        stale = (now - dt.timedelta(seconds=600)).isoformat()
        board = MarketBoard("e", "s", "", "A", "B", "h2h", books=[
            BookOdds("fresh", "h2h", [Outcome("A", 1.80), Outcome("B", 2.20)],
                     last_update=recent),
            BookOdds("stale", "h2h", [Outcome("A", 2.20), Outcome("B", 1.80)],
                     last_update=stale),
        ])
        no_recency = consensus_lines_from_boards(
            [board], method="weighted", min_books=2, recency_halflife=0.0)[0]
        with_recency = consensus_lines_from_boards(
            [board], method="weighted", min_books=2, recency_halflife=60.0)[0]
        # Fresh book favours A (1.80 -> higher prob); recency should raise A's prob.
        self.assertGreater(with_recency.probs["A"], no_recency.probs["A"])


if __name__ == "__main__":
    unittest.main()
