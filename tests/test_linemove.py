import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.bot import ValueBettingBot
from bot.config import Config
from bot.linemove import LineTracker
from bot.models import ValueBet


class TestLineTracker(unittest.TestCase):
    def test_move_reports_change(self):
        t = LineTracker()
        k = LineTracker.key("e", "A")
        t.update(k, 0.45, 2.0, now=100.0)
        t.update(k, 0.52, 2.0, now=160.0)
        d_prob, d_price = t.move(k, window_seconds=900, now=160.0)
        self.assertAlmostEqual(d_prob, 0.07, places=6)   # sharp moved toward A
        self.assertAlmostEqual(d_price, 0.0, places=6)   # Betfair lagged (unchanged)

    def test_none_without_history(self):
        t = LineTracker()
        t.update(LineTracker.key("e", "A"), 0.5, 2.0, now=100.0)
        self.assertIsNone(t.move(LineTracker.key("e", "A"), 900, now=100.0))
        self.assertIsNone(t.move(LineTracker.key("e", "B"), 900, now=100.0))

    def test_window_excludes_old_points(self):
        t = LineTracker()
        k = LineTracker.key("e", "A")
        t.update(k, 0.40, 2.0, now=0.0)       # far outside a 60s window
        t.update(k, 0.50, 2.0, now=1000.0)
        t.update(k, 0.55, 2.0, now=1030.0)
        d_prob, _ = t.move(k, window_seconds=60, now=1030.0)
        self.assertAlmostEqual(d_prob, 0.05, places=6)  # 0.55 - 0.50, not - 0.40


def _bet(**kw):
    base = dict(event_id="e", sport_key="s", commence_time="", matchup="A vs B",
                market="h2h", selection="A", bookmaker="betfair", price=2.2,
                fair_prob=0.5, fair_price=2.0, edge=0.05, ev=0.05,
                kelly_fraction=0.1, stake=10.0)
    base.update(kw)
    return ValueBet(**base)


def _bot(**cfg_kw):
    d = tempfile.mkdtemp()
    cfg = Config(pinnacle_source="sample", venue_source="sample",
                 db_path=os.path.join(d, "l.db"), csv_path=None, **cfg_kw)
    return ValueBettingBot(cfg)


class TestMovementFilter(unittest.TestCase):
    def _seed(self, bot, early_prob, late_prob):
        k = LineTracker.key("e", "A")
        now = time.time()
        bot._tracker.update(k, early_prob, 2.0, now=now - 60)
        bot._tracker.update(k, late_prob, 2.2, now=now)

    def test_adverse_move_blocked(self):
        bot = _bot(block_adverse_sharp_move=True, adverse_move_threshold=0.02)
        self._seed(bot, 0.55, 0.50)  # sharp moved DOWN 0.05 -> falling knife
        self.assertEqual(bot._movement_filter([_bet()]), [])
        bot.close()

    def test_favourable_move_allowed_and_annotated(self):
        bot = _bot(block_adverse_sharp_move=True)
        self._seed(bot, 0.45, 0.50)  # sharp moved UP 0.05 toward A
        kept = bot._movement_filter([_bet()])
        self.assertEqual(len(kept), 1)
        self.assertAlmostEqual(kept[0].sharp_move, 0.05, places=6)
        bot.close()

    def test_require_move_blocks_without_lag(self):
        bot = _bot(require_sharp_move=True, min_sharp_move=0.01)
        # No favourable move (single observation -> move is None).
        bot._tracker.update(LineTracker.key("e", "A"), 0.5, 2.0)
        self.assertEqual(bot._movement_filter([_bet()]), [])
        bot.close()

    def test_require_move_allows_with_lag(self):
        bot = _bot(require_sharp_move=True, min_sharp_move=0.01)
        self._seed(bot, 0.45, 0.50)
        self.assertEqual(len(bot._movement_filter([_bet()])), 1)
        bot.close()

    def test_disabled_passes_through(self):
        bot = _bot(block_adverse_sharp_move=False, require_sharp_move=False)
        self._seed(bot, 0.55, 0.50)  # would be adverse, but filtering is off
        self.assertEqual(len(bot._movement_filter([_bet()])), 1)
        bot.close()


if __name__ == "__main__":
    unittest.main()
