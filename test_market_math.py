import unittest
import math
from market_math import implied_probability, no_vig_probabilities, expected_value, brier_score, log_loss


class MarketMathTests(unittest.TestCase):
    def test_american_odds(self):
        self.assertAlmostEqual(implied_probability(-120), 120 / 220)
        self.assertAlmostEqual(implied_probability(150), 100 / 250)

    def test_no_vig_removes_overround(self):
        probs = no_vig_probabilities([-110, -110])
        self.assertAlmostEqual(sum(probs), 1.0)
        self.assertAlmostEqual(probs[0], 0.5)

    def test_three_way_market(self):
        self.assertAlmostEqual(sum(no_vig_probabilities([120, 220, 300])), 1.0)

    def test_ev(self):
        self.assertAlmostEqual(expected_value(0.6, 100), 0.2)
        self.assertAlmostEqual(expected_value(0.5, -110), -0.0454545454545454)

    def test_perfect_and_imperfect_predictions(self):
        self.assertAlmostEqual(brier_score([1, 0], [1, 0]), 0)
        self.assertAlmostEqual(brier_score([0.5, 0.5], [1, 0]), 0.25)
        self.assertAlmostEqual(log_loss([0.5, 0.5], [1, 0]), math.log(2))

    def test_extreme_log_loss_is_finite(self):
        self.assertTrue(math.isfinite(log_loss([0, 1], [1, 0])))

    def test_bad_inputs(self):
        for odds in [0, -50, 50, float("nan")]:
            with self.subTest(odds=odds), self.assertRaises(ValueError):
                implied_probability(odds)
        with self.assertRaises(ValueError):
            no_vig_probabilities([-110])
        with self.assertRaises(ValueError):
            expected_value(1.1, 100)
        with self.assertRaises(ValueError):
            brier_score([0.5], [2])
        with self.assertRaises(ValueError):
            brier_score([0.5], [1, 0])


if __name__ == "__main__":
    unittest.main()
