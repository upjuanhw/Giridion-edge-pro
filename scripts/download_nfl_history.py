"""Download NFL regular season and postseason completed games from ESPN.

Usage: python scripts/download_nfl_history.py --start 2018 --end 2026 --output data/nfl_games.csv
Only final games are included. Does not download odds, injuries or advanced statistics.
"""
import argparse
import csv
import sys
import time
from pathlib import Path

import requests

URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
FIELDS = ("event_id", "season", "season_type", "week", "kickoff_utc",
          "home_id", "home", "away_id", "away", "home_score", "away_score",
          "winner", "source")


def parse_event(event, season, season_type, week):
    if not event.get("status", {}).get("type", {}).get("completed"):
        return None
    competitions = event.get("competitions") or []
    if not competitions:
        return None
    participants = competitions[0].get("competitors") or []
    home = next((c for c in participants if c.get("homeAway") == "home"), None)
    away = next((c for c in participants if c.get("homeAway") == "away"), None)
    if home is None or away is None:
        return None
    try:
        hs, a_s = int(home["score"]), int(away["score"])
    except (KeyError, ValueError, TypeError):
        return None
    ht, at = home.get("team") or {}, away.get("team") or {}
    return dict(event_id=str(event.get("id", "")), season=season,
                season_type="regular" if season_type == 2 else "postseason",
                week=week, kickoff_utc=event.get("date", ""),
                home_id=str(ht.get("id", "")), home=ht.get("displayName", ""),
                away_id=str(at.get("id", "")), away=at.get("displayName", ""),
                home_score=hs, away_score=a_s,
                winner="tie" if hs == a_s else ("home" if hs > a_s else "away"),
                source="ESPN scoreboard")


def fetch_games(start, end, delay=0.1, session=None):
    if end < start:
        raise ValueError("end must be >= start")
    session = session or requests.Session()
    session.headers.update({"User-Agent": "GiridionEdgePro/0.5 (historical research)"})
    games, failures = {}, []
    for season in range(start, end + 1):
        for season_type, max_week in ((2, 18), (3, 5)):
            for week in range(1, max_week + 1):
                try:
                    resp = session.get(URL, params={
                        "dates": str(season), "seasontype": season_type,
                        "week": week, "limit": 100
                    }, timeout=25)
                    resp.raise_for_status()
                    for event in resp.json().get("events", []):
                        row = parse_event(event, season, season_type, week)
                        if row and row["event_id"]:
                            games[row["event_id"]] = row
                except (requests.RequestException, ValueError) as exc:
                    failures.append(f"{season} type {season_type} week {week}: {exc}")
                if delay:
                    time.sleep(delay)
    return sorted(games.values(), key=lambda r: (r["kickoff_utc"], r["event_id"])), failures


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=2018)
    parser.add_argument("--end", type=int, default=2026)
    parser.add_argument("--output", default="data/nfl_games.csv")
    args = parser.parse_args()
    rows, failures = fetch_games(args.start, args.end)
    if not rows:
        print("No completed NFL games; refusing to write empty CSV", file=sys.stderr)
        return 1
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved {len(rows)} completed NFL games across seasons {args.start}-{args.end}")
    for failure in failures:
        print(f"WARNING {failure}", file=sys.stderr)
    return 2 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
