import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    "download_nfl_history", Path(__file__).parent / "scripts" / "download_nfl_history.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class NFLDownloaderTest(unittest.TestCase):
    def test_completed_and_tie(self):
        event = {"id": "1", "date": "2026-10-25T17:00Z",
                 "status": {"type": {"completed": True}},
                 "competitions": [{"competitors": [
                     {"homeAway": "home", "score": "20", "team": {"id": "1", "displayName": "A"}},
                     {"homeAway": "away", "score": "20", "team": {"id": "2", "displayName": "B"}}
                 ]}]}
        self.assertEqual(module.parse_event(event, 2026, 2, 8)["winner"], "tie")
        event["status"]["type"]["completed"] = False
        self.assertIsNone(module.parse_event(event, 2026, 2, 8))


if __name__ == "__main__":
    unittest.main()
