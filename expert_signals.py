"""External NFL expert signals for Giridion Edge Pro.

Manual inputs only: no unlicensed scraping or fabricated live probabilities.
"""
from dataclasses import dataclass
from math import log, exp
from typing import Optional

NFL_EXPERTS = ("Jeremy Bergman", "Brooke Cersosimo", "Gennaro Filice", "Bobby Kownack", "Dan Parr")

@dataclass(frozen=True)
class SquawkaSignal:
    home_win_probability: float
    projected_home_margin: float
    source_url: str
    as_of: str

    def __post_init__(self):
        if not 0 <= self.home_win_probability <= 1:
            raise ValueError("home_win_probability must be between 0 and 1")


def nfl_expert_consensus(predictions: dict):
    """Predictions: expert name -> (home_score, away_score)."""
    valid = {name: scores for name, scores in predictions.items()
             if name in NFL_EXPERTS and scores is not None}
    if not valid:
        raise ValueError("At least one NFL.com expert score is required")
    for scores in valid.values():
        if len(scores) != 2 or any(not isinstance(v, (int, float)) or v < 0 for v in scores):
            raise ValueError("Scores must be nonnegative numbers")
    n = len(valid)
    margins = [h-a for h, a in valid.values()]
    totals = [h+a for h, a in valid.values()]
    return {
        "experts_count": n,
        "home_picks": sum(m > 0 for m in margins),
        "away_picks": sum(m < 0 for m in margins),
        "ties": sum(m == 0 for m in margins),
        "home_pick_share": sum(m > 0 for m in margins)/n,
        "average_home_margin": sum(margins)/n,
        "average_total": sum(totals)/n,
    }


def blend_probabilities(own_probability: float, external_probability: Optional[float], external_weight: float = 0.15):
    """Optional exploratory log-odds blend, NOT calibrated EV certification."""
    if not 0 < own_probability < 1:
        raise ValueError("own_probability must be strictly between 0 and 1")
    if external_probability is None:
        return own_probability
    if not 0 < external_probability < 1 or not 0 <= external_weight <= 1:
        raise ValueError("Invalid external probability or weight")
    own_logit = log(own_probability/(1-own_probability))
    external_logit = log(external_probability/(1-external_probability))
    z = (1-external_weight)*own_logit + external_weight*external_logit
    return 1/(1+exp(-z))


def expected_value(probability: float, american_odds: int):
    if not 0 <= probability <= 1 or american_odds == 0:
        raise ValueError("Invalid probability or odds")
    profit = american_odds/100 if american_odds > 0 else 100/abs(american_odds)
    return probability*profit-(1-probability)
