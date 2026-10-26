"""Unit tests for The Odds API adapter; no network calls or secrets required."""
import unittest
from unittest.mock import patch, Mock
from odds_provider import fetch_odds


class OddsProviderTests(unittest.TestCase):
    @patch("odds_provider.requests.get")
    def test_nfl_url_and_market_parameters(self, get):
        response = Mock()
        response.json.return_value = [{
            "home_team": "Pittsburgh Steelers",
            "away_team": "Cleveland Browns",
            "commence_time": "2026-11-01T18:00:00Z",
            "bookmakers": [{"title": "Example Book", "markets": [
                {"key": "h2h", "outcomes": [{"name": "Pittsburgh Steelers", "price": -120}]}
            ]}]
        }]
        get.return_value = response
        rows = fetch_odds("NFL", "dummy-test-key")
        args, kwargs = get.call_args
        self.assertEqual(args[0], "https://api.the-odds-api.com/v4/sports/americanfootball_nfl/odds/")
        self.assertEqual(kwargs["params"]["markets"], "h2h,spreads,totals")
        self.assertEqual(kwargs["params"]["apiKey"], "dummy-test-key")
        self.assertEqual(rows.iloc[0]["Momio americano"], -120)
        self.assertEqual(rows.iloc[0]["Mercado"], "ML")

    @patch("odds_provider.requests.get")
    def test_ncaaf_endpoint(self, get):
        get.return_value.json.return_value = []
        fetch_odds("NCAAF", "dummy-test-key")
        self.assertIn("/americanfootball_ncaaf/odds/", get.call_args.args[0])

    def test_reject_missing_key_and_invalid_league(self):
        with self.assertRaises(ValueError):
            fetch_odds("NFL", "")
        with self.assertRaises(ValueError):
            fetch_odds("NBA", "dummy-test-key")


if __name__ == "__main__":
    unittest.main()
