import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import run as cli


def _args(extra):
    d = tempfile.mkdtemp()
    return ["--config", os.path.join(d, "nope.yaml")] + extra


class TestCliSmoke(unittest.TestCase):
    """Exercise the read-only / one-shot commands end to end on sample data."""

    def test_doctor_passes_on_sample(self):
        self.assertEqual(cli.main(_args(["doctor"])), 0)

    def test_status_runs(self):
        self.assertEqual(cli.main(_args(["status"])), 0)

    def test_scan_runs(self):
        self.assertEqual(cli.main(_args(["scan"])), 0)

    def test_run_one_shot(self):
        self.assertEqual(cli.main(_args(["run"])), 0)

    def test_report_runs(self):
        self.assertEqual(cli.main(_args(["report"])), 0)

    def test_backtest_synthetic(self):
        self.assertEqual(cli.main(_args(["backtest", "--synthetic", "300"])), 0)

    def test_live_without_creds_refuses(self):
        # 'go --live' with no Betfair creds must refuse to start (exit 2).
        code = cli.main(_args(["go", "--budget", "100", "--stake", "5", "--live"]))
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
