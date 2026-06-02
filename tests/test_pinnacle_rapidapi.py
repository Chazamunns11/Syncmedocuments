import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.pinnacle import pinnacle_lines_from_rapidapi_json

SAMPLE = {
    "events": [
        {
            "event_id": 1572384,
            "sport_id": 1,
            "starts": "2026-06-03T18:00:00Z",
            "home": "Arsenal",
            "away": "Chelsea",
            "last_update": "2026-06-03T17:45:00Z",
            "periods": {
                "num_0": {"money_line": {"home": 2.10, "draw": 3.40, "away": 3.60}},
            },
        },
        {  # two-way (tennis), no draw
            "event_id": 1572999,
            "sport_id": 2,
            "starts": "2026-06-03T12:00:00Z",
            "home": "Player A",
            "away": "Player B",
            "periods": {"num_0": {"money_line": {"home": 1.55, "away": 2.55}}},
        },
        {"event_id": 1, "home": "X", "away": "Y", "periods": {}},  # no odds -> skip
    ]
}


class TestRapidAPIParser(unittest.TestCase):
    def test_parses_three_way_and_devigs(self):
        lines = pinnacle_lines_from_rapidapi_json(SAMPLE, "soccer", "multiplicative")
        self.assertEqual(len(lines), 2)  # third event skipped (no money line)
        soc = lines[0]
        self.assertEqual(soc.event_key, "1572384")
        self.assertEqual(set(soc.probs), {"Arsenal", "Draw", "Chelsea"})
        self.assertAlmostEqual(sum(soc.probs.values()), 1.0, places=6)  # de-vigged
        self.assertGreater(soc.overround, 1.0)  # raw book had margin
        self.assertEqual(soc.source, "pinnacle")

    def test_two_way_market(self):
        lines = pinnacle_lines_from_rapidapi_json(SAMPLE, "tennis", "multiplicative")
        two = [l for l in lines if l.event_key == "1572999"][0]
        self.assertEqual(set(two.probs), {"Player A", "Player B"})
        self.assertAlmostEqual(sum(two.probs.values()), 1.0, places=6)
        self.assertGreater(two.probs["Player A"], two.probs["Player B"])  # favourite

    def test_empty_and_garbage(self):
        self.assertEqual(pinnacle_lines_from_rapidapi_json({}, "soccer"), [])
        self.assertEqual(pinnacle_lines_from_rapidapi_json({"events": None}, "soccer"), [])


if __name__ == "__main__":
    unittest.main()
