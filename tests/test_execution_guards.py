import datetime as dt
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.bot import ValueBettingBot
from bot.config import Config
from bot.models import FairLine


def _iso(seconds_ago):
    return (dt.datetime.now(dt.timezone.utc)
            - dt.timedelta(seconds=seconds_ago)).isoformat()


class TestStaleGuard(unittest.TestCase):
    def _bot(self, **kw):
        d = tempfile.mkdtemp()
        cfg = Config(pinnacle_source="sample", venue_source="sample",
                     db_path=os.path.join(d, "s.db"), csv_path=None, **kw)
        return ValueBettingBot(cfg)

    def test_drops_stale_lines(self):
        bot = self._bot(max_line_age_seconds=60)
        fresh = FairLine("e1", "s", "", "A", "B", "h2h", {"A": 0.5},
                         last_update=_iso(10))
        stale = FairLine("e2", "s", "", "C", "D", "h2h", {"C": 0.5},
                         last_update=_iso(600))
        out = bot._drop_stale([fresh, stale])
        self.assertEqual([fl.event_key for fl in out], ["e1"])
        bot.close()

    def test_keeps_when_no_timestamp_or_disabled(self):
        bot = self._bot(max_line_age_seconds=60)
        no_ts = FairLine("e", "s", "", "A", "B", "h2h", {"A": 0.5})
        self.assertEqual(len(bot._drop_stale([no_ts])), 1)
        bot.close()
        bot2 = self._bot(max_line_age_seconds=0)  # disabled
        stale = FairLine("e", "s", "", "A", "B", "h2h", {"A": 0.5},
                         last_update=_iso(99999))
        self.assertEqual(len(bot2._drop_stale([stale])), 1)
        bot2.close()


class TestLiveOnlyGuards(unittest.TestCase):
    def test_guard_and_settle_noop_in_paper(self):
        d = tempfile.mkdtemp()
        cfg = Config(pinnacle_source="sample", venue_source="sample",
                     executor="paper", live=False,
                     db_path=os.path.join(d, "n.db"), csv_path=None)
        bot = ValueBettingBot(cfg)
        # Must be safe no-ops without a Betfair session.
        self.assertEqual(bot.guard_unmatched(), 0)
        self.assertEqual(bot.auto_settle(), 0)
        bot.close()


if __name__ == "__main__":
    unittest.main()
