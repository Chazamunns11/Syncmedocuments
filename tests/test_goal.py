import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import run as cli
from bot.bankroll import BankrollManager
from bot.bot import ValueBettingBot
from bot.config import Config
from bot.models import BookOdds, MarketBoard, Outcome, ValueBet
from bot.scheduler import ContinuousRunner
from bot.value import ValueDetector


def _two_value_board():
    """One event where TWO selections look like value (so one-per-event matters)."""
    return MarketBoard(
        event_id="evt", sport_key="s", commence_time="", home_team="A",
        away_team="B", market="h2h",
        fair_probs={"A": 0.5, "B": 0.5}, fair_source="weighted", overround=1.0,
        books=[BookOdds("betfair", "h2h", [
            Outcome("A", 2.30, selection_id="1", size=500),
            Outcome("B", 2.25, selection_id="2", size=500),
        ], market_id="1.1")],
    )


class TestOnePerEvent(unittest.TestCase):
    def test_detector_keeps_one_per_event(self):
        det = ValueDetector(commission=0.0, min_edge=0.01, one_per_event=True)
        bets = det.detect([_two_value_board()])
        self.assertEqual(len(bets), 1)
        self.assertEqual(bets[0].selection, "A")  # higher edge

    def test_can_disable(self):
        det = ValueDetector(commission=0.0, min_edge=0.01, one_per_event=False)
        self.assertEqual(len(det.detect([_two_value_board()])), 2)


class TestExpectedCLV(unittest.TestCase):
    def test_exp_clv_computed_and_positive(self):
        det = ValueDetector(commission=0.05, min_edge=0.0, min_expected_clv=0.0)
        bet = det.detect([_two_value_board()])[0]
        # exp_clv is gross overlay: 2.30 / 2.00 - 1 = 0.15
        self.assertAlmostEqual(bet.exp_clv, 0.15, places=6)
        self.assertGreater(bet.exp_clv, 0.0)

    def test_min_expected_clv_filters(self):
        det = ValueDetector(commission=0.0, min_edge=0.0, min_expected_clv=0.20)
        # Overlay is only 0.15 < 0.20 -> rejected.
        self.assertEqual(det.detect([_two_value_board()]), [])


class TestFlatStake(unittest.TestCase):
    def test_flat_stake_used(self):
        mgr = BankrollManager(bankroll=1000, flat_stake=25.0, max_stake=1000,
                              min_stake=1.0)
        bet = ValueBet(event_id="e", sport_key="s", commence_time="", matchup="m",
                       market="h2h", selection="A", bookmaker="betfair", price=2.0,
                       fair_prob=0.5, fair_price=2.0, edge=0.05, ev=0.05,
                       kelly_fraction=0.5, available_size=500)
        self.assertEqual(mgr.stake_for(bet), 25.0)

    def test_flat_stake_capped_by_liquidity(self):
        mgr = BankrollManager(bankroll=1000, flat_stake=100.0, max_stake=1000,
                              min_stake=1.0)
        bet = ValueBet(event_id="e", sport_key="s", commence_time="", matchup="m",
                       market="h2h", selection="A", bookmaker="betfair", price=2.0,
                       fair_prob=0.5, fair_price=2.0, edge=0.05, ev=0.05,
                       kelly_fraction=0.5, available_size=40)
        self.assertEqual(mgr.stake_for(bet), 40.0)


class TestEventDedupAndClvCapture(unittest.TestCase):
    def test_one_bet_per_event_across_runs_and_clv_capture(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = Config(truth_model="weighted", pinnacle_source="sample",
                         venue_source="sample", executor="betfair", live=False,
                         min_edge=0.01, db_path=os.path.join(d, "g.db"),
                         csv_path=None)
            bot = ValueBettingBot(cfg)
            try:
                # Place once: the in-window event (Arsenal vs Chelsea, ~2 min out).
                runner = ContinuousRunner(bot, place_window_minutes=5.0,
                                          min_seconds_before_start=0.0,
                                          closing_capture_seconds=999999,  # force capture
                                          max_cycles=1)
                placed = runner.run_once()
                self.assertEqual(len(placed), 1)
                ev = placed[0][0].event_id

                # Same event must not be bet again.
                self.assertTrue(bot.store.already_placed_event(ev))
                self.assertEqual(runner.run_once(), [])

                # CLV was captured (closing snapshot forced) -> summary has it.
                s = bot.store.summary()
                self.assertEqual(s["clv_n"], 1)
                self.assertIsNotNone(s["avg_exp_clv"])
            finally:
                bot.close()


class TestGoCommand(unittest.TestCase):
    def test_go_applies_overrides(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = Config(pinnacle_source="sample", venue_source="sample",
                         db_path=os.path.join(d, "go.db"), csv_path=None)

            class Args:
                budget, kelly, stake, max_stake, min_clv, live = \
                    500.0, None, 20.0, 75.0, 0.01, False
            captured = {}

            def fake_watch(c):
                captured.update(bankroll=c.bankroll, flat=c.flat_stake,
                                maxs=c.max_stake, clv=c.min_expected_clv)
                return 0
            orig = cli.cmd_watch
            cli.cmd_watch = fake_watch
            try:
                cli.cmd_go(cfg, Args())
            finally:
                cli.cmd_watch = orig
            self.assertEqual(captured["bankroll"], 500.0)
            self.assertEqual(captured["flat"], 20.0)
            self.assertEqual(captured["maxs"], 75.0)
            self.assertEqual(captured["clv"], 0.01)


if __name__ == "__main__":
    unittest.main()
