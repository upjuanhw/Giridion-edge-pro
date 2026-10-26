"""Minimal upset-finder ranking and walk-forward evaluation utilities.

All features and odds must be snapshots available before kickoff.
No automatic sportsbook integration or trained model is implied.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import log
from typing import Iterable


def american_to_decimal(odds: int) -> float:
    if odds == 0:
        raise ValueError("American odds cannot be zero")
    return 1 + odds / 100 if odds > 0 else 1 + 100 / abs(odds)


def implied_probability(odds: int) -> float:
    return 1 / american_to_decimal(odds)


def no_vig_probability(team_odds: int, opponent_odds: int) -> float:
    """Two-way proportional vig removal; both sides must be available."""
    a = implied_probability(team_odds)
    b = implied_probability(opponent_odds)
    return a / (a + b)


@dataclass(frozen=True)
class Candidate:
    game_id: str
    team: str
    opponent: str
    kickoff_utc: str
    snapshot_utc: str
    moneyline: int
    win_probability: float
    opponent_moneyline: int | None = None

    def __post_init__(self) -> None:
        if not 0 <= self.win_probability <= 1:
            raise ValueError("win_probability must be in [0, 1]")
        if self.snapshot_utc >= self.kickoff_utc:
            raise ValueError("Odds/features snapshot must precede kickoff")

    @property
    def expected_roi(self) -> float:
        return self.win_probability * american_to_decimal(self.moneyline) - 1

    @property
    def edge(self) -> float:
        baseline = (
            no_vig_probability(self.moneyline, self.opponent_moneyline)
            if self.opponent_moneyline is not None
            else implied_probability(self.moneyline)
        )
        return self.win_probability - baseline


def rank_upsets(candidates: Iterable[Candidate], min_moneyline: int = 200, top_n: int = 10,
                sort_by: str = "probability") -> list[Candidate]:
    """One pick per game; prioritize highest win probability or highest EV."""
    if sort_by not in {"probability", "ev", "edge"}:
        raise ValueError("sort_by must be probability, ev, or edge")
    eligible = [c for c in candidates if c.moneyline >= min_moneyline]
    metric = {
        "probability": lambda c: c.win_probability,
        "ev": lambda c: c.expected_roi,
        "edge": lambda c: c.edge,
    }[sort_by]
    eligible.sort(key=lambda c: (metric(c), c.win_probability), reverse=True)
    seen = set()
    result = []
    for c in eligible:
        if c.game_id in seen:
            continue
        seen.add(c.game_id)
        result.append(c)
        if len(result) >= top_n:
            break
    return result


def brier_score(probabilities: Iterable[float], outcomes: Iterable[int]) -> float:
    pairs = list(zip(probabilities, outcomes))
    if not pairs:
        raise ValueError("No observations")
    if any(y not in (0, 1) or not 0 <= p <= 1 for p, y in pairs):
        raise ValueError("Invalid probabilities or outcomes")
    return sum((p - y) ** 2 for p, y in pairs) / len(pairs)


def log_loss(probabilities: Iterable[float], outcomes: Iterable[int]) -> float:
    pairs = list(zip(probabilities, outcomes))
    if not pairs:
        raise ValueError("No observations")
    eps = 1e-12
    return -sum(y * log(max(eps, min(1-eps, p))) +
                (1-y) * log(max(eps, min(1-eps, 1-p))) for p, y in pairs) / len(pairs)
