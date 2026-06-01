import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.bankroll import BankrollManager
from bot.bot import ValueBettingBot
from bot.config import Config
from bot.devig import power, multiplicative, devig
from bot.models import BookOdds, MarketBoard, Outcome, ValueBet
from bot.scheduler import ContinuousRunner
from bot.store import BetStore
from bot.value import ValueDetector


def _bet(**kw):
    base = dict(
        event_id="e", sport_key="s", commence_time="", matchup="A vs B",
        market="h2h", selection="A", bookmaker="betfair", price=2.2,
        fair_prob=0.5, fair_price=2.0, edge=0.05, ev=0.05, kelly_fraction=0.1,
    )
    base.update(kw)
    return ValueBet(**base)


class TestPowerDevig(unittest.TestCase):
    def test_sums_to_one_and_favourite_higher(self):
        probs = power([1.50, 2.70])
        self.assertAlmostEqual(sum(probs), 1.0, places=9)
        self.assertGreater(probs[0], probs[1])

    def test_shrinks_favourite_vs_multiplicative(self):
        odds = [1.20, 6.0]
        self.assertLess(power(odds)[0], multiplicative(odds)[0] + 1e-9)

    def test_three_way_sums_to_one(self):
        probs = devig([2.4, 3.3, 3.1], "power")
        self.assertAlmostEqual(sum(probs), 1.0, places=8)


class TestDetectorFilters(unittest.TestCase):
    def _board(self, pinnacle_odds, betfair_price, size=500.0):
        names = ["A", "B"]
        return MarketBoard(
            event_id="e", sport_key="s", commence_time="", home_team="A",
            away_team="B", market="h2h",
            books=[
                BookOdds("pinnacle", "h2h",
                         [Outcome(n, o) for n, o in zip(names, pinnacle_odds)]),
                BookOdds("betfair", "h2h",
                         [Outcome("A", betfair_price, selection_id="1", size=size),
                          Outcome("B", 2.0, selection_id="2", size=size)],
                         market_id="1.1"),
            ],
        )

    def test_overround_band_rejects_wide_markets(self):
        # Pinnacle 1.5/1.5 -> booksum 1.333, above the 1.15 band -> rejected.
        board = self._board([1.5, 1.5], betfair_price=2.5)
        det = ValueDetector(reference_books=["pinnacle"], max_overround=1.15,
                            commission=0.0, min_edge=0.01)
        self.assertEqual(det.detect([board]), [])
        # With a permissive band the value is found.
        det2 = ValueDetector(reference_books=["pinnacle"], max_overround=2.0,
                             commission=0.0, min_edge=0.01)
        self.assertTrue(det2.detect([board]))

    def test_liquidity_filter(self):
        board = self._board([2.0, 2.0], betfair_price=2.3, size=5.0)
        det = ValueDetector(reference_books=["pinnacle"], min_liquidity=50.0,
                            commission=0.0, min_edge=0.01)
        self.assertEqual(det.detect([board]), [])

    def test_edge_haircut_reduces_edge(self):
        board = self._board([2.0, 2.0], betfair_price=2.3)
        det = ValueDetector(reference_books=["pinnacle"], edge_haircut=0.05,
                            commission=0.0, min_edge=0.0)
        bets = det.detect([board])
        self.assertTrue(bets)
        # Gross overlay is 0.15 (2.3 vs fair 2.0); haircut leaves ~0.10.
        self.assertAlmostEqual(bets[0].edge, 0.15 - 0.05, places=6)


class TestLiquidityStakeCap(unittest.TestCase):
    def test_stake_capped_to_available_size(self):
        mgr = BankrollManager(bankroll=100000, kelly_multiplier=1.0,
                              max_fraction_per_bet=1.0, min_stake=1.0,
                              max_stake=1e9)
        stake = mgr.stake_for(_bet(kelly_fraction=0.5, available_size=7.0))
        self.assertLessEqual(stake, 7.0)


class TestStoreDedupAndCLV(unittest.TestCase):
    def test_dedup_and_clv(self):
        with tempfile.TemporaryDirectory() as d:
            store = BetStore(db_path=os.path.join(d, "s.db"), csv_path=None)
            from bot.execution.paper import PaperExecutor
            bet = _bet(commission=0.05, eff_price=2.14)
            self.assertFalse(store.already_placed(bet.key))
            res = PaperExecutor(seed=1).place(bet)
            store.log_placement(res, bet)
            self.assertTrue(store.already_placed(bet.key))

            clv = store.record_closing(res.external_ref, closing_fair_price=2.30)
            # Taken ~2.20 vs closing fair 2.30 -> negative CLV.
            self.assertLess(clv, 0)
            clv2_ref = res.external_ref
            clv2 = store.record_closing(clv2_ref, closing_fair_price=2.05)
            self.assertGreater(clv2, 0)  # taken 2.20 beat closing fair 2.05
            store.close()


class TestScheduler(unittest.TestCase):
    def test_is_due_window(self):
        runner = ContinuousRunner(bot=None, place_window_minutes=3.0,
                                  min_seconds_before_start=20.0,
                                  now_fn=lambda: 1000.0)
        # event 100s out -> inside [20, 180] window -> due
        soon = "1970-01-01T00:18:20+00:00"  # epoch 1100 = now+100
        self.assertTrue(runner._is_due(_bet(commence_time=soon)))
        # event 2h out -> not due
        far = "1970-01-01T02:00:00+00:00"
        self.assertFalse(runner._is_due(_bet(commence_time=far)))

    def test_next_sleep_short_when_in_window(self):
        runner = ContinuousRunner(bot=None, poll_interval=60.0,
                                  refresh_interval=5.0, place_window_minutes=3.0,
                                  now_fn=lambda: 1000.0)
        in_window = _bet(commence_time="1970-01-01T00:18:20+00:00")  # now+100
        self.assertEqual(runner._next_sleep([in_window]), 5.0)

    def test_run_once_places_then_dedups(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = Config(mode="pinnacle_betfair", pinnacle_source="sample",
                         venue_source="sample", executor="betfair", live=False,
                         min_edge=0.01, edge_haircut=0.0,
                         db_path=os.path.join(d, "w.db"),
                         csv_path=os.path.join(d, "w.csv"))
            bot = ValueBettingBot(cfg)
            try:
                runner = ContinuousRunner(bot, place_window_minutes=5.0,
                                          min_seconds_before_start=0.0,
                                          max_cycles=1)
                # Event 1 in sample data starts ~2 min out -> inside 5-min window.
                placed = runner.run_once()
                self.assertTrue(placed, "expected a near-kickoff placement")
                # Second pass must dedup (no new placements for same selection).
                self.assertEqual(runner.run_once(), [])
            finally:
                bot.close()


if __name__ == "__main__":
    unittest.main()
