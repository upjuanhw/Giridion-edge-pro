import unittest
from upset_finder import Candidate, american_to_decimal, implied_probability, no_vig_probability, rank_upsets, brier_score, log_loss


class TestUpsetFinder(unittest.TestCase):
    def make(self, game, odds, prob):
        return Candidate(game, "A", "B", "2026-10-31T18:00:00Z",
                         "2026-10-30T18:00:00Z", odds, prob)

    def test_odds(self):
        self.assertAlmostEqual(american_to_decimal(200), 3)
        self.assertAlmostEqual(american_to_decimal(-150), 1 + 100/150)
        self.assertAlmostEqual(implied_probability(200), 1/3)
        self.assertAlmostEqual(no_vig_probability(100, 100), .5)

    def test_filter_and_rank(self):
        items = [self.make("1", 210, .30), self.make("2", 195, .60),
                 self.make("3", 300, .26)]
        self.assertEqual([x.game_id for x in rank_upsets(items)], ["1", "3"])
        self.assertEqual([x.game_id for x in rank_upsets(items, sort_by="ev")], ["3", "1"])

    def test_no_leakage(self):
        with self.assertRaises(ValueError):
            Candidate("1", "A", "B", "2026-10-31T18:00:00Z",
                      "2026-10-31T18:00:00Z", 200, .4)

    def test_scores(self):
        self.assertAlmostEqual(brier_score([.8, .2], [1, 0]), .04)
        self.assertAlmostEqual(log_loss([.5], [1]), .69314718056)


if __name__ == "__main__":
    unittest.main()
