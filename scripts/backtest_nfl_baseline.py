"""NFL chronological baseline: Elo win probabilities and pregame margin/total estimates.

This is a research baseline, not a calibrated sportsbook betting model.
Predictions for each UTC calendar day use ratings/stats from earlier days only.
"""
import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path


def run(rows, k=24., elo_home_adv=55., points_home_adv=1.5, regression=0.12):
    ratings = defaultdict(lambda: 1500.)
    # Per-team exponentially weighted points scored and allowed (initialized to league mean).
    scored = defaultdict(lambda: 22.)
    allowed = defaultdict(lambda: 22.)
    days = defaultdict(list)
    for row in rows:
        days[row["kickoff_utc"][:10]].append(row)
    output = []
    for day in sorted(days):
        changes = defaultdict(float)
        next_scored, next_allowed = {}, {}
        for row in days[day]:
            home = row["home_id"] or row["home"]
            away = row["away_id"] or row["away"]
            if home == away:
                continue
            hs, a_s = int(row["home_score"]), int(row["away_score"])
            p_home = 1 / (1 + 10 ** ((ratings[away] - ratings[home] - elo_home_adv)/400))
            predicted_home_points = (scored[home] + allowed[away])/2 + points_home_adv/2
            predicted_away_points = (scored[away] + allowed[home])/2 - points_home_adv/2
            margin = predicted_home_points - predicted_away_points
            total = predicted_home_points + predicted_away_points
            if hs != a_s:
                result = 1 if hs > a_s else 0
                delta = k * (result - p_home)
                changes[home] += delta
                changes[away] -= delta
                brier = (p_home - result)**2
            else:
                result, brier = "tie", ""
                delta = k * (.5 - p_home)
                changes[home] += delta
                changes[away] -= delta
            output.append(dict(event_id=row["event_id"], kickoff_utc=row["kickoff_utc"],
                               season=row["season"], season_type=row["season_type"],
                               home=row["home"], away=row["away"],
                               predicted_home_win_prob=round(p_home, 6),
                               predicted_home_margin=round(margin, 3),
                               predicted_total=round(total, 3),
                               actual_home_margin=hs-a_s, actual_total=hs+a_s,
                               home_won=result, brier=round(brier, 6) if brier != "" else ""))
            next_scored[home] = (1-regression)*scored[home] + regression*hs
            next_allowed[home] = (1-regression)*allowed[home] + regression*a_s
            next_scored[away] = (1-regression)*scored[away] + regression*a_s
            next_allowed[away] = (1-regression)*allowed[away] + regression*hs
        for team, delta in changes.items():
            ratings[team] += delta
        scored.update(next_scored)
        allowed.update(next_allowed)
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--historical", default="data/nfl_2018_2025.csv")
    parser.add_argument("--current", default="data/nfl_2026_completed.csv")
    parser.add_argument("--output", default="data/nfl_baseline_backtest.csv")
    args = parser.parse_args()
    rows = []
    for filename in (args.historical, args.current):
        with open(filename, newline="", encoding="utf-8") as f:
            rows.extend(csv.DictReader(f))
    rows = list({r["event_id"]: r for r in rows}.values())
    predictions = run(rows)
    if not predictions:
        raise ValueError("No NFL games for evaluation")
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=predictions[0].keys())
        writer.writeheader()
        writer.writerows(predictions)
    scored = [r for r in predictions if r["brier"] != ""]
    brier = sum(r["brier"] for r in scored)/len(scored)
    margin_mae = sum(abs(r["predicted_home_margin"] - r["actual_home_margin"]) for r in predictions)/len(predictions)
    total_mae = sum(abs(r["predicted_total"] - r["actual_total"]) for r in predictions)/len(predictions)
    print(f"NFL BACKTEST games={len(predictions)} brier={brier:.4f} margin_mae={margin_mae:.2f} total_mae={total_mae:.2f}")
    print("CAUTION: no odds/spreads/totals from sportsbooks; cannot estimate betting ROI or ATS/OU hit rate.")
    print("CAUTION: uncalibrated simple baseline; no season resets, roster changes, injury inputs or market comparisons.")


if __name__ == "__main__":
    main()
