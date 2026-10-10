import unittest
import pandas as pd
from data_quality import audit_games, is_clean
from historical_model import clean_games, predict

class DataQualityTests(unittest.TestCase):
    def setUp(self):
        self.games = pd.DataFrame([
            {"date":"2025-09-01","home":"A","away":"B","home_score":20,"away_score":17},
            {"date":"2025-09-08","home":"B","away":"A","home_score":14,"away_score":24},
        ])

    def test_clean_input(self):
        self.assertTrue(is_clean(audit_games(self.games)))

    def test_duplicate(self):
        data = pd.concat([self.games, self.games.iloc[[0]]], ignore_index=True)
        self.assertEqual(audit_games(data)["duplicate_matchups"], 1)

    def test_invalid_scores_and_dates(self):
        data = self.games.copy()
        data.loc[0, "home_score"] = -3
        data.loc[1, "date"] = "bad date"
        findings = audit_games(data)
        self.assertEqual(findings["invalid_scores"], 1)
        self.assertEqual(findings["invalid_dates"], 1)

    def test_fractional_score_is_rejected(self):
        data = self.games.copy()
        data.loc[0, "home_score"] = 20.5
        self.assertEqual(audit_games(data)["invalid_scores"], 1)
        self.assertEqual(len(clean_games(data)), 1)

    def test_same_kickoff_is_not_training_data(self):
        from historical_model import backtest
        dates = ["2025-09-01"] * 35
        data = pd.DataFrame([
            {"date": dates[i], "home": "A" if i % 2 == 0 else "B",
             "away": "B" if i % 2 == 0 else "A",
             "home_score": 20, "away_score": 17} for i in range(35)
        ])
        self.assertTrue(backtest(clean_games(data), min_history=30).empty)

    def test_missing_columns(self):
        with self.assertRaises(ValueError):
            audit_games(pd.DataFrame({"home": ["A"]}))

    def test_model_probabilities_sum_to_one(self):
        games = clean_games(self.games)
        p = predict(games, "A", "B", simulations=2000)
        self.assertAlmostEqual(p["home_win"] + p["away_win"] + p["tie"], 1.0, places=8)
        self.assertGreaterEqual(p["total"], 0)

if __name__ == "__main__":
    unittest.main()
