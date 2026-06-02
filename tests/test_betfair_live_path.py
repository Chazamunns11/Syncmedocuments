"""Mock tests for the Betfair live path (placement + price parsing).

These never hit the network: they feed fake betfairlightweight-shaped objects
into the REAL parsing/placement code so the live path — which can't otherwise be
exercised without an account — is verified for correctness.
"""
import os
import sys
import types
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.betfair_client import BetfairClient
from bot.execution.betfair import BetfairExecutor
from bot.models import ValueBet


def _bet(**kw):
    base = dict(event_id="e", sport_key="s", commence_time="", matchup="A vs B",
                market="h2h", selection="A", bookmaker="betfair", price=2.2,
                fair_prob=0.5, fair_price=2.0, edge=0.05, ev=0.05,
                kelly_fraction=0.1, stake=10.0,
                venue_market_id="1.23", venue_selection_id="4567")
    base.update(kw)
    return ValueBet(**base)


# --- fake betfairlightweight response objects ---------------------------
class _Instr:
    def __init__(self, size_matched=None, avg=None, bet_id=None, error_code=None):
        self.size_matched = size_matched
        self.average_price_matched = avg
        self.bet_id = bet_id
        self.error_code = error_code


class _Report:
    def __init__(self, status, instrs):
        self.status = status
        self.place_instruction_reports = instrs


class _FakeClientForExec:
    """Minimal stand-in passed as BetfairExecutor(client=...)."""
    def __init__(self, report):
        self._report = report
        self.captured = None

    def place_back(self, market_id, selection_id, price, size, persistence="LAPSE"):
        self.captured = dict(market_id=market_id, selection_id=selection_id,
                             price=price, size=size)
        return self._report

    def trading(self):
        raise AssertionError("should not need a live session when ids are present")

    def close(self):
        pass


class TestBetfairPlacement(unittest.TestCase):
    def test_dry_run_does_not_send(self):
        ex = BetfairExecutor(client=_FakeClientForExec(None), dry_run=True)
        res = ex.place(_bet())
        self.assertEqual(res.status, "DRY_RUN")
        self.assertEqual(res.external_ref, "1.23:4567")

    def test_matched_order_parsed(self):
        report = _Report("SUCCESS", [_Instr(size_matched=10.0, avg=2.18,
                                            bet_id="BET99")])
        fake = _FakeClientForExec(report)
        ex = BetfairExecutor(client=fake, dry_run=False)
        res = ex.place(_bet())
        self.assertEqual(res.status, "MATCHED")
        self.assertEqual(res.matched_stake, 10.0)
        self.assertEqual(res.matched_price, 2.18)
        self.assertEqual(res.external_ref, "BET99")
        # The right market/selection/size/price were sent.
        self.assertEqual(fake.captured["market_id"], "1.23")
        self.assertEqual(fake.captured["selection_id"], "4567")
        self.assertEqual(fake.captured["size"], 10.0)

    def test_unmatched_limit_is_placed_status(self):
        report = _Report("SUCCESS", [_Instr(size_matched=0.0, bet_id="BET1")])
        ex = BetfairExecutor(client=_FakeClientForExec(report), dry_run=False)
        self.assertEqual(ex.place(_bet()).status, "PLACED")

    def test_failure_status_is_rejected(self):
        report = _Report("FAILURE", [_Instr(error_code="INSUFFICIENT_FUNDS")])
        ex = BetfairExecutor(client=_FakeClientForExec(report), dry_run=False)
        res = ex.place(_bet())
        self.assertEqual(res.status, "REJECTED")
        self.assertIn("FAILURE", res.message)


# --- fake API client for price parsing ----------------------------------
class _PriceSize:
    def __init__(self, price, size):
        self.price = price
        self.size = size


class _Ex:
    def __init__(self, backs):
        self.available_to_back = backs


class _Runner:
    def __init__(self, sid, backs):
        self.selection_id = sid
        self.ex = _Ex(backs)


class _Book:
    def __init__(self, market_id, runners):
        self.market_id = market_id
        self.runners = runners


class _Cat:
    def __init__(self, market_id, runners, event_name, start=None):
        self.market_id = market_id
        self.runners = runners
        self.event = types.SimpleNamespace(name=event_name)
        self.market_start_time = start


class _CatRunner:
    def __init__(self, sid, name):
        self.selection_id = sid
        self.runner_name = name


class _Betting:
    def __init__(self, books, catalogues=None):
        self._books = books
        self._catalogues = catalogues or []
        self.placed = None

    def list_market_book(self, market_ids, price_projection):
        return self._books

    def list_market_catalogue(self, filter, market_projection, max_results,
                              sort=None):
        return self._catalogues

    def place_orders(self, market_id, instructions):
        self.placed = dict(market_id=market_id, instructions=instructions)
        return _Report("SUCCESS", [_Instr(size_matched=instructions[0]["limitOrder"]["size"],
                                          avg=instructions[0]["limitOrder"]["price"],
                                          bet_id="OK")])


class _FakeApi:
    def __init__(self, books, catalogues=None):
        self.betting = _Betting(books, catalogues)


class TestPlaceBackAndCatalogue(unittest.TestCase):
    def test_place_back_rounds_to_valid_tick(self):
        bc = BetfairClient("u", "p", "k")
        bc._client = _FakeApi([])
        # 2.234 is not a valid Betfair tick; must round to 2.24 (step 0.02).
        bc.place_back("1.1", "55", price=2.234, size=12.0)
        instr = bc._client.betting.placed["instructions"][0]
        self.assertEqual(bc._client.betting.placed["market_id"], "1.1")
        self.assertEqual(instr["selectionId"], 55)
        self.assertEqual(instr["side"], "BACK")
        self.assertEqual(instr["limitOrder"]["price"], 2.24)
        self.assertEqual(instr["limitOrder"]["size"], 12.0)

    def test_list_match_odds_caches_catalogue_and_prices(self):
        bc = BetfairClient("u", "p", "k")
        cats = [_Cat("1.77", [_CatRunner(11, "Arsenal"), _CatRunner(22, "Chelsea")],
                     "Arsenal v Chelsea")]
        books = [_Book("1.77", [_Runner(11, [_PriceSize(2.5, 100.0)]),
                                _Runner(22, [_PriceSize(3.0, 80.0)])])]
        bc._client = _FakeApi(books, cats)
        quotes = bc.list_match_odds(event_type_id="1")
        self.assertEqual(len(quotes), 2)
        self.assertIn("1.77", bc._catalogue)  # catalogue cached for fast refresh
        self.assertEqual(bc._catalogue["1.77"]["home"], "Arsenal")


class TestBetfairPriceParsing(unittest.TestCase):
    def test_refresh_prices_builds_quotes(self):
        bc = BetfairClient("u", "p", "k")
        # Pre-seed the catalogue cache (as list_match_odds would).
        bc._catalogue["1.50"] = {
            "names": {"11": "Arsenal", "22": "Chelsea"},
            "event_name": "Arsenal v Chelsea", "home": "Arsenal",
            "away": "Chelsea", "start": "2026-06-02T18:00:00Z"}
        books = [_Book("1.50", [
            _Runner(11, [_PriceSize(2.20, 350.0), _PriceSize(2.18, 100.0)]),
            _Runner(22, [_PriceSize(3.60, 200.0)]),
        ])]
        bc._client = _FakeApi(books)  # bypass login
        quotes = bc.refresh_prices(["1.50"])
        self.assertEqual(len(quotes), 2)
        ars = next(q for q in quotes if q.selection_id == "11")
        self.assertEqual(ars.runner_name, "Arsenal")
        self.assertEqual(ars.price, 2.20)   # best (first) back price
        self.assertEqual(ars.size, 350.0)
        self.assertEqual(ars.home_team, "Arsenal")

    def test_runner_with_no_back_is_skipped(self):
        bc = BetfairClient("u", "p", "k")
        bc._catalogue["1.9"] = {"names": {"1": "X"}, "event_name": "X v Y",
                                "home": "X", "away": "Y", "start": ""}
        bc._client = _FakeApi([_Book("1.9", [_Runner(1, [])])])
        self.assertEqual(bc.refresh_prices(["1.9"]), [])


if __name__ == "__main__":
    unittest.main()
