import datetime as dt
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.freshness import assess_freshness, line_age_seconds
from bot.models import FairLine


def _line(ts):
    return FairLine(event_key="e", sport_key="s", commence_time="", home_team="H",
                    away_team="A", market="h2h", probs={"H": 0.5, "A": 0.5},
                    last_update=ts)


NOW = dt.datetime(2026, 6, 2, 12, 0, 0, tzinfo=dt.timezone.utc)


class TestFreshness(unittest.TestCase):
    def test_age_computation(self):
        ln = _line("2026-06-02T11:59:30Z")  # 30s old
        self.assertAlmostEqual(line_age_seconds(ln, NOW), 30.0, places=1)

    def test_no_timestamp_returns_none(self):
        self.assertIsNone(line_age_seconds(_line(None), NOW))

    def test_fresh_feed(self):
        lines = [_line("2026-06-02T11:59:55Z"), _line("2026-06-02T11:59:50Z"),
                 _line("2026-06-02T11:59:58Z")]  # all <10s
        r = assess_freshness(lines, threshold_seconds=30.0, now=NOW)
        self.assertTrue(r.fresh_enough)
        self.assertEqual(r.n_timestamped, 3)
        self.assertLessEqual(r.median_age, 10)

    def test_stale_feed_flagged(self):
        lines = [_line("2026-06-02T11:55:00Z"), _line("2026-06-02T11:57:00Z")]  # 3-5 min
        r = assess_freshness(lines, threshold_seconds=30.0, now=NOW)
        self.assertFalse(r.fresh_enough)
        self.assertIn("STALE", r.message)

    def test_no_timestamps_cannot_judge(self):
        r = assess_freshness([_line(None), _line(None)], now=NOW)
        self.assertFalse(r.fresh_enough)
        self.assertEqual(r.n_timestamped, 0)


if __name__ == "__main__":
    unittest.main()
