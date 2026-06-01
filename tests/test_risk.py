import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.execution.paper import PaperExecutor
from bot.models import PlacementResult, ValueBet
from bot.risk import RiskLimits, RiskManager
from bot.store import BetStore


def _store(d):
    return BetStore(db_path=os.path.join(d, "r.db"), csv_path=None)


def _placement(stake, status="MATCHED", settlement=None, profit=None):
    bet = ValueBet(event_id="e", sport_key="s", commence_time="", matchup="m",
                   market="h2h", selection="A", bookmaker="betfair", price=2.0,
                   fair_prob=0.5, fair_price=2.0, edge=0.05, ev=0.05,
                   kelly_fraction=0.1, stake=stake)
    res = PlacementResult(bet_key=bet.key, executor="paper", status=status,
                          requested_price=2.0, requested_stake=stake,
                          matched_stake=stake, external_ref="x")
    return bet, res


class TestRiskBreakers(unittest.TestCase):
    def test_bankroll_floor_halts(self):
        with tempfile.TemporaryDirectory() as d:
            store = _store(d)
            rm = RiskManager(RiskLimits(starting_bankroll=1000,
                                        min_bankroll_fraction=0.5), store)
            ok, reason = rm.status(400)  # below 500 floor
            self.assertFalse(ok)
            self.assertIn("floor", reason)
            store.close()

    def test_drawdown_stop_loss_halts(self):
        with tempfile.TemporaryDirectory() as d:
            store = _store(d)
            rm = RiskManager(RiskLimits(starting_bankroll=1000,
                                        stop_loss_fraction=0.30,
                                        min_bankroll_fraction=0.0), store)
            store.set_meta("peak_bankroll", 1200)
            ok, reason = rm.status(800)  # 33% down from peak 1200
            self.assertFalse(ok)
            self.assertIn("drawdown", reason)
            store.close()

    def test_daily_stake_cap_limits_stake(self):
        with tempfile.TemporaryDirectory() as d:
            store = _store(d)
            # Already staked 240 today; daily limit 25% of 1000 = 250 -> 10 left.
            from bot.models import utcnow_iso
            for _ in range(4):
                bet, res = _placement(60.0)
                store.log_placement(res, bet)
            rm = RiskManager(RiskLimits(starting_bankroll=1000,
                                        daily_stake_limit_fraction=0.25), store)
            capped = rm.cap_stake(50.0, 1000)
            self.assertAlmostEqual(capped, 10.0, places=2)
            store.close()

    def test_open_exposure_cap(self):
        with tempfile.TemporaryDirectory() as d:
            store = _store(d)
            # 200 open (unsettled); exposure limit 25% of 1000 = 250 -> 50 left.
            for _ in range(4):
                bet, res = _placement(50.0)
                store.log_placement(res, bet)
            rm = RiskManager(RiskLimits(starting_bankroll=1000,
                                        max_open_exposure_fraction=0.25,
                                        daily_stake_limit_fraction=1.0), store)
            self.assertAlmostEqual(rm.cap_stake(80.0, 1000), 50.0, places=2)
            store.close()

    def test_max_open_bets_halts(self):
        with tempfile.TemporaryDirectory() as d:
            store = _store(d)
            for _ in range(3):
                bet, res = _placement(10.0)
                store.log_placement(res, bet)
            rm = RiskManager(RiskLimits(starting_bankroll=1000, max_open_bets=3),
                             store)
            ok, reason = rm.status(1000)
            self.assertFalse(ok)
            self.assertIn("open bets", reason)
            store.close()


class TestCompoundBankroll(unittest.TestCase):
    def test_bankroll_compounds_from_realised(self):
        from bot.config import Config
        from bot.bot import ValueBettingBot
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "c.db")
            cfg = Config(pinnacle_source="sample", venue_source="sample",
                         bankroll=1000, db_path=db, csv_path=None)
            bot = ValueBettingBot(cfg)
            bet, res = _placement(50.0)
            res.external_ref = "BET1"
            bot.store.log_placement(res, bet)
            bot.store.settle_from_betfair([type("O", (), {"bet_id": "BET1",
                                                          "profit": 200.0})()])
            bot.refresh_bankroll()
            self.assertAlmostEqual(bot.bankroll.bankroll, 1200.0, places=2)
            bot.close()


class TestBotHalts(unittest.TestCase):
    def test_place_bets_halts_on_breach(self):
        from bot.config import Config
        from bot.bot import ValueBettingBot
        with tempfile.TemporaryDirectory() as d:
            cfg = Config(pinnacle_source="sample", venue_source="sample",
                         bankroll=1000, min_bankroll_fraction=0.5,
                         compound_bankroll=False,
                         db_path=os.path.join(d, "h.db"), csv_path=None)
            bot = ValueBettingBot(cfg)
            bot.bankroll.bankroll = 100  # force below floor
            placed = bot.place_bets(bot.evaluate())
            self.assertEqual(placed, [])
            bot.close()


if __name__ == "__main__":
    unittest.main()
