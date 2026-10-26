"""Download FBS regular-season final scores from ESPN's public scoreboard.

Usage:
    python scripts/download_ncaaf_history.py --start 2018 --end 2025 --output data/ncaaf_games_2018_2025.csv

Only completed games are saved. No betting odds or pregame features are implied.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys
import time

import requests

ENDPOINT = "https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard"
FIELDS = ("event_id", "season", "week", "date", "home_id", "home", "away_id",
          "away", "home_score", "away_score", "winner", "source")


def parse_event(event: dict, season: int, week: int) -> dict | None:
    if not event.get("status", {}).get("type", {}).get("completed"):
        return None
    competitions = event.get("competitions") or []
    if not competitions:
        return None
    competitors = competitions[0].get("competitors") or []
    home = next((c for c in competitors if c.get("homeAway") == "home"), None)
    away = next((c for c in competitors if c.get("homeAway") == "away"), None)
    if not home or not away:
        return None
    try:
        hs, a_s = int(home["score"]), int(away["score"])
    except (ValueError, TypeError, KeyError):
        return None
    if hs == a_s:
        return None
    home_team, away_team = home.get("team") or {}, away.get("team") or {}
    return dict(event_id=str(event.get("id", "")), season=season, week=week,
                date=event.get("date", ""), home_id=str(home_team.get("id", "")),
                home=home_team.get("displayName", ""), away_id=str(away_team.get("id", "")),
                away=away_team.get("displayName", ""), home_score=hs, away_score=a_s,
                winner="home" if hs > a_s else "away", source="ESPN scoreboard")


def fetch_history(start: int, end: int, sleep_seconds: float = .15,
                  session: requests.Session | None = None) -> tuple[list[dict], list[str]]:
    if end < start:
        raise ValueError("end must be >= start")
    session = session or requests.Session()
    session.headers.update({"User-Agent": "GiridionEdgePro/0.4 (historical research)"})
    games, failures = {}, []
    for season in range(start, end + 1):
        for week in range(1, 17):
            try:
                response = session.get(ENDPOINT, params={
                    "dates": str(season), "seasontype": 2, "week": week,
                    "limit": 500, "groups": 80,
                }, timeout=25)
                response.raise_for_status()
                payload = response.json()
                for event in payload.get("events", []):
                    parsed = parse_event(event, season, week)
                    if parsed and parsed["event_id"]:
                        games[parsed["event_id"]] = parsed
            except (requests.RequestException, ValueError) as exc:
                failures.append(f"{season} week {week}: {exc}")
            if sleep_seconds:
                time.sleep(sleep_seconds)
    return sorted(games.values(), key=lambda r: (r["date"], r["event_id"])), failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=2018)
    parser.add_argument("--end", type=int, default=2025)
    parser.add_argument("--output", default="data/ncaaf_games_2018_2025.csv")
    args = parser.parse_args()
    rows, failures = fetch_history(args.start, args.end)
    if not rows:
        print("No games downloaded; not writing empty dataset", file=sys.stderr)
        return 1
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved {len(rows)} completed games to {target}")
    if failures:
        print(f"WARNING: {len(failures)} failed weekly requests; dataset may be incomplete",
              file=sys.stderr)
        for failure in failures:
            print(f"  {failure}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
