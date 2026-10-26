import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("nfl_baseline", Path(__file__).parent / "scripts" / "backtest_nfl_baseline.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class NFLBaselineTest(unittest.TestCase):
    def test_prior_game_only(self):
        def row(i, date, home_score, away_score):
            return {"event_id": str(i), "kickoff_utc": date, "season": "2026",
                    "season_type": "regular", "home_id": "1", "away_id": "2",
                    "home": "Home", "away": "Away", "home_score": str(home_score),
                    "away_score": str(away_score)}
        result = module.run([row(1, "2026-09-01T17:00:00Z", 30, 10),
                             row(2, "2026-09-08T17:00:00Z", 20, 10)])
        self.assertEqual(len(result), 2)
        self.assertAlmostEqual(result[0]["predicted_total"], 44)
        self.assertGreater(result[1]["predicted_home_win_prob"], result[0]["predicted_home_win_prob"])


if __name__ == "__main__":
    unittest.main()
