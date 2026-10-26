"""Chronological Elo baseline using only past results; no sportsbook odds."""
import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path


def run(rows, k=24.0, home_advantage=55.0, scale=400.0):
    ratings = defaultdict(lambda: 1500.0)
    results = []
    # Group same-date games: no results from a simultaneous calendar day can leak.
    days = defaultdict(list)
    for row in rows:
        days[row["date"][:10]].append(row)
    for date in sorted(days):
        updates = defaultdict(float)
        for row in days[date]:
            home, away = row["home_id"] or row["home"], row["away_id"] or row["away"]
            if home == away:
                continue
            p_home = 1 / (1 + 10 ** ((ratings[away] - ratings[home] - home_advantage) / scale))
            outcome = int(int(row["home_score"]) > int(row["away_score"]))
            p_winner = p_home if outcome else 1-p_home
            underdog_p = min(p_home, 1-p_home)
            underdog_won = (outcome == 1 and p_home < .5) or (outcome == 0 and p_home > .5)
            results.append(dict(date=date, season=row["season"], home=row["home"],
                                away=row["away"], p_home=round(p_home, 6),
                                home_won=outcome, brier=round((p_home-outcome)**2, 6),
                                underdog_probability=round(underdog_p, 6),
                                model_underdog_won=int(underdog_won)))
            delta = k * (outcome - p_home)
            updates[home] += delta
            updates[away] -= delta
        for team, delta in updates.items():
            ratings[team] += delta
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/ncaaf_games.csv")
    parser.add_argument("--output", default="data/ncaaf_elo_backtest.csv")
    args = parser.parse_args()
    with open(args.input, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    results = run(rows)
    if not results:
        raise ValueError("No backtest rows")
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    brier = sum(r["brier"] for r in results) / len(results)
    n_underdogs = sum(r["model_underdog_won"] for r in results)
    print(f"BACKTEST games={len(results)} brier={brier:.4f} model_underdog_wins={n_underdogs}")
    print("CAUTION: model underdogs are NOT verified betting-market underdogs; no ML/ROI data.")
    print("CAUTION: fixed Elo settings; not tuned, calibrated, or evaluated against market.")
    print("CAUTION: season continuity and same-day date batching are simplified.")


if __name__ == "__main__":
    main()
