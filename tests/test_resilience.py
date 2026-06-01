import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot import http
from bot.config import Config


class _Resp:
    def __init__(self, status=200, headers=None):
        self.status_code = status
        self.headers = headers or {}

    def json(self):
        return {"ok": True}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class _Session:
    """Fake session yielding a scripted sequence of responses/exceptions."""
    def __init__(self, script):
        self.script = list(script)
        self.calls = 0

    def request(self, method, url, **kw):
        self.calls += 1
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class TestHttpRetries(unittest.TestCase):
    def test_retries_on_connection_error_then_succeeds(self):
        sess = _Session([ConnectionError("boom"), ConnectionError("boom"), _Resp(200)])
        resp = http.request("GET", "http://x", session=sess, retries=4,
                            backoff=0.0, sleep_fn=lambda s: None)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(sess.calls, 3)

    def test_retries_on_429_then_succeeds(self):
        sess = _Session([_Resp(429, {"Retry-After": "0"}), _Resp(200)])
        resp = http.request("GET", "http://x", session=sess, retries=4,
                            backoff=0.0, sleep_fn=lambda s: None)
        self.assertEqual(resp.status_code, 200)

    def test_raises_after_exhausting_retries(self):
        sess = _Session([ConnectionError("a"), ConnectionError("b")])
        with self.assertRaises(ConnectionError):
            http.request("GET", "http://x", session=sess, retries=1,
                         backoff=0.0, sleep_fn=lambda s: None)

    def test_get_json_returns_payload_and_headers(self):
        sess = _Session([_Resp(200, {"x-requests-remaining": "42"})])
        data, headers = http.get_json("http://x", session=sess,
                                      sleep_fn=lambda s: None)
        self.assertEqual(data["ok"], True)
        self.assertEqual(headers["x-requests-remaining"], "42")


class TestConfigValidation(unittest.TestCase):
    def test_good_config_has_no_errors(self):
        errs = [m for m in Config().validate() if m.startswith("ERROR")]
        self.assertEqual(errs, [])

    def test_bad_values_flagged(self):
        c = Config(bankroll=-1, kelly_multiplier=2.0, betfair_commission=0.9,
                   max_stake=1, min_stake=50)
        errs = [m for m in c.validate() if m.startswith("ERROR")]
        self.assertTrue(any("bankroll" in m for m in errs))
        self.assertTrue(any("kelly" in m for m in errs))
        self.assertTrue(any("commission" in m for m in errs))
        self.assertTrue(any("max_stake" in m for m in errs))

    def test_live_without_creds_errors(self):
        c = Config(live=True, executor="betfair")
        self.assertTrue(any("BETFAIR_USERNAME" in m for m in c.validate()))


if __name__ == "__main__":
    unittest.main()
