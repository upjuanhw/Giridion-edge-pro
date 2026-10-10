"""Transparent baseline for historical football results; not calibrated betting advice."""
import numpy as np
import pandas as pd

REQUIRED = {"date", "home", "away", "home_score", "away_score"}

def clean_games(df):
    missing = REQUIRED - set(df.columns)
    if missing:
        raise ValueError("Columnas faltantes: " + ", ".join(sorted(missing)))
    out = df.copy()
    out["date"] = pd.to_datetime(out["date"], errors="coerce", utc=True)
    for col in ("home_score", "away_score"):
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out["home"] = out["home"].astype(str).str.strip()
    out["away"] = out["away"].astype(str).str.strip()
    out = out.dropna(subset=["date", "home_score", "away_score"])
    out = out[(out.home != "") & (out.away != "") & (out.home != out.away)]
    out = out[(out.home_score >= 0) & (out.away_score >= 0)]
    out = out[(out.home_score % 1 == 0) & (out.away_score % 1 == 0)]
    return out.sort_values("date").reset_index(drop=True)

def team_profile(games, team, baseline=23.0, shrink=5):
    home = games[games.home == team]
    away = games[games.away == team]
    scored = np.r_[home.home_score.to_numpy(), away.away_score.to_numpy()]
    allowed = np.r_[home.away_score.to_numpy(), away.home_score.to_numpy()]
    n = len(scored)
    return {
        "n": n,
        "offense": float((scored.sum() + shrink * baseline) / (n + shrink)),
        "defense": float((allowed.sum() + shrink * baseline) / (n + shrink)),
    }

def predict(games, home, away, home_advantage=1.5, sd=10.5, simulations=20000, seed=42):
    if home == away:
        raise ValueError("Selecciona dos equipos diferentes.")
    if games.empty:
        raise ValueError("No hay partidos históricos válidos.")
    league_mean = float((games.home_score.sum() + games.away_score.sum()) / (2 * len(games)))
    hp = team_profile(games, home, league_mean)
    ap = team_profile(games, away, league_mean)
    # Equal blend of attack and opposing defense, shrunk to league average.
    expected_home = max(0, (hp["offense"] + ap["defense"]) / 2 + home_advantage)
    expected_away = max(0, (ap["offense"] + hp["defense"]) / 2)
    rng = np.random.default_rng(seed)
    hs = np.maximum(0, np.rint(rng.normal(expected_home, sd, simulations)))
    vs = np.maximum(0, np.rint(rng.normal(expected_away, sd, simulations)))
    return {"home_mean": expected_home, "away_mean": expected_away,
            "home_win": float(np.mean(hs > vs)), "away_win": float(np.mean(vs > hs)),
            "tie": float(np.mean(hs == vs)), "total": float(expected_home + expected_away),
            "home_games": hp["n"], "away_games": ap["n"],
            "home_scores": hs, "away_scores": vs}

def backtest(games, min_history=30):
    """Strict chronological expanding window; no future scores in training."""
    rows = []
    ordered = games.sort_values("date").reset_index(drop=True)
    for i in range(min_history, len(ordered)):
        game = ordered.iloc[i]
        training = ordered[ordered.date < game.date]  # No same-kickoff look-ahead
        if (training.home.eq(game.home) | training.away.eq(game.home)).sum() < 3:
            continue
        if (training.home.eq(game.away) | training.away.eq(game.away)).sum() < 3:
            continue
        p = predict(training, game.home, game.away, simulations=4000, seed=i)
        outcome = int(game.home_score > game.away_score)
        if game.home_score == game.away_score:
            continue
        rows.append({"date": game.date, "match": f"{game.away} @ {game.home}",
                     "prob_home": p["home_win"], "home_won": outcome,
                     "brier": (p["home_win"] - outcome) ** 2,
                     "predicted_total": p["total"],
                     "actual_total": game.home_score + game.away_score})
    return pd.DataFrame(rows)
