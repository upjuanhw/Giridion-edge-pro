"""Auditable market probability and forecast evaluation primitives.

No odds feed, recommendation engine, or profitability claims.
"""
import math


def implied_probability(american_odds):
    """Raw implied probability, including bookmaker margin."""
    odds = float(american_odds)
    if not math.isfinite(odds) or odds == 0 or -100 < odds < 100:
        raise ValueError("American odds must be <= -100 or >= +100")
    return 100 / (odds + 100) if odds > 0 else -odds / (-odds + 100)


def no_vig_probabilities(american_odds):
    """Proportional normalization of a complete mutually exclusive market."""
    prices = list(american_odds)
    if len(prices) < 2:
        raise ValueError("At least two outcomes required")
    raw = [implied_probability(x) for x in prices]
    total = sum(raw)
    if total <= 0:
        raise ValueError("Invalid market")
    return [p / total for p in raw]


def expected_value(probability, american_odds):
    """Expected net profit per unit staked, before taxes/fees."""
    p = float(probability)
    if not math.isfinite(p) or not 0 <= p <= 1:
        raise ValueError("Probability must be in [0, 1]")
    odds = float(american_odds)
    implied_probability(odds)
    net_win = odds / 100 if odds > 0 else 100 / abs(odds)
    return p * net_win - (1 - p)


def brier_score(probabilities, outcomes):
    """Binary Brier score; lower is better."""
    ps, ys = list(probabilities), list(outcomes)
    if not ps or len(ps) != len(ys):
        raise ValueError("Equal nonempty probability and outcome sequences required")
    if any(not math.isfinite(float(p)) or not 0 <= float(p) <= 1 for p in ps):
        raise ValueError("Probabilities must be in [0, 1]")
    if any(y not in (0, 1) for y in ys):
        raise ValueError("Outcomes must be binary")
    return sum((float(p) - y) ** 2 for p, y in zip(ps, ys)) / len(ps)


def log_loss(probabilities, outcomes, epsilon=1e-15):
    """Binary logarithmic loss with finite clipping."""
    ps, ys = list(probabilities), list(outcomes)
    brier_score(ps, ys)  # Validate all inputs.
    total = 0.0
    for p, y in zip(ps, ys):
        q = min(1 - epsilon, max(epsilon, float(p)))
        total -= y * math.log(q) + (1 - y) * math.log1p(-q)
    return total / len(ps)
