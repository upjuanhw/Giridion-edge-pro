import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    "download_ncaaf_history", Path(__file__).parent / "scripts" / "download_ncaaf_history.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class TestHistoricalLoader(unittest.TestCase):
    def test_parse_final(self):
        event = {
            "id": "123", "date": "2025-10-04T18:00Z",
            "status": {"type": {"completed": True}},
            "competitions": [{"competitors": [
                {"homeAway": "home", "score": "24",
                 "team": {"id": "1", "displayName": "Home"}},
                {"homeAway": "away", "score": "31",
                 "team": {"id": "2", "displayName": "Away"}},
            ]}],
        }
        row = module.parse_event(event, 2025, 6)
        self.assertEqual(row["winner"], "away")
        self.assertEqual(row["away_score"], 31)
        event["status"]["type"]["completed"] = False
        self.assertIsNone(module.parse_event(event, 2025, 6))


if __name__ == "__main__":
    unittest.main()
