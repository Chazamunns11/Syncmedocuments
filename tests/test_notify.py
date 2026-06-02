import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.notify import Notifier
from bot.models import PlacementResult, ValueBet


def _bet():
    return ValueBet(event_id="e", sport_key="s", commence_time="", matchup="A vs B",
                    market="h2h", selection="A", bookmaker="betfair", price=2.2,
                    fair_prob=0.5, fair_price=2.0, edge=0.05, ev=0.05,
                    kelly_fraction=0.1, stake=10.0, exp_clv=0.09)


class TestNotifier(unittest.TestCase):
    def test_disabled_without_url(self):
        n = Notifier(webhook_url=None)
        self.assertFalse(n.enabled)
        self.assertFalse(n.send("hi"))

    def test_sends_via_poster(self):
        sent = []
        n = Notifier(webhook_url="http://hook", poster=lambda u, p: sent.append((u, p)))
        self.assertTrue(n.send("hello"))
        self.assertEqual(sent[0][0], "http://hook")
        self.assertEqual(sent[0][1], {"text": "hello"})

    def test_bet_and_halt_messages(self):
        sent = []
        n = Notifier(webhook_url="http://hook", poster=lambda u, p: sent.append(p["text"]))
        res = PlacementResult(bet_key="k", executor="paper", status="MATCHED",
                              requested_price=2.2, requested_stake=10.0,
                              external_ref="X1")
        n.bet_placed(_bet(), res)
        n.halt("drawdown stop-loss")
        self.assertTrue(any("MATCHED" in m and "exp-CLV" in m for m in sent))
        self.assertTrue(any("RISK HALT" in m for m in sent))

    def test_failure_is_swallowed(self):
        def boom(u, p):
            raise ConnectionError("down")
        n = Notifier(webhook_url="http://hook", poster=boom)
        self.assertFalse(n.send("x"))  # must not raise

    def test_respects_toggles(self):
        sent = []
        n = Notifier(webhook_url="http://hook", on_bets=False,
                     poster=lambda u, p: sent.append(p))
        res = PlacementResult(bet_key="k", executor="paper", status="MATCHED",
                              requested_price=2.2, requested_stake=10.0)
        n.bet_placed(_bet(), res)
        self.assertEqual(sent, [])


class TestDailySummary(unittest.TestCase):
    def test_sends_once_per_day(self):
        from bot.config import Config
        from bot.bot import ValueBettingBot
        from bot.scheduler import ContinuousRunner
        with tempfile.TemporaryDirectory() as d:
            cfg = Config(pinnacle_source="sample", venue_source="sample",
                         notify_webhook_url="http://hook",
                         db_path=os.path.join(d, "s.db"), csv_path=None)
            bot = ValueBettingBot(cfg)
            sent = []
            bot.notifier._poster = lambda u, p: sent.append(p["text"])
            # Fixed clock -> same UTC day across calls.
            runner = ContinuousRunner(bot, now_fn=lambda: 1_000_000.0)
            runner._maybe_daily_summary()
            runner._maybe_daily_summary()  # same day -> no second send
            self.assertEqual(len([m for m in sent if "Daily" in m]), 1)
            bot.close()


class TestBotIntegration(unittest.TestCase):
    def test_halt_notifies(self):
        from bot.config import Config
        from bot.bot import ValueBettingBot
        with tempfile.TemporaryDirectory() as d:
            cfg = Config(pinnacle_source="sample", venue_source="sample",
                         bankroll=1000, min_bankroll_fraction=0.5,
                         compound_bankroll=False, notify_webhook_url="http://hook",
                         db_path=os.path.join(d, "n.db"), csv_path=None)
            bot = ValueBettingBot(cfg)
            sent = []
            bot.notifier._poster = lambda u, p: sent.append(p["text"])
            bot.bankroll.bankroll = 100  # below floor -> halt
            bot.place_bets(bot.evaluate())
            self.assertTrue(any("RISK HALT" in m for m in sent))
            bot.close()


if __name__ == "__main__":
    unittest.main()
