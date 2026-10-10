"""Public ESPN scoreboard season loader. Unofficial, best-effort data source."""
import requests
import pandas as pd

def fetch_season(league, year):
    sport = "nfl" if league == "NFL" else "college-football"
    weeks = range(1, 19) if league == "NFL" else range(1, 17)
    endpoint = f"https://site.api.espn.com/apis/site/v2/sports/football/{sport}/scoreboard"
    session = requests.Session()
    session.headers.update({"User-Agent": "GridironEdgePro/0.3"})
    rows = {}
    errors = 0
    for week in weeks:
        try:
            response = session.get(endpoint, params={"dates": str(year), "seasontype": 2, "week": week, "limit": 500, "groups": 80 if league == "NCAAF" else None}, timeout=12)
            response.raise_for_status()
            for event in response.json().get("events", []):
                competition = (event.get("competitions") or [{}])[0]
                status = event.get("status", {}).get("type", {})
                if not status.get("completed", False):
                    continue
                teams = competition.get("competitors", [])
                home = next((x for x in teams if x.get("homeAway") == "home"), None)
                away = next((x for x in teams if x.get("homeAway") == "away"), None)
                if not home or not away:
                    continue
                try:
                    hs, vs = int(home["score"]), int(away["score"])
                except (KeyError, ValueError, TypeError):
                    continue
                rows[str(event.get("id", ""))] = {
                    "date": event.get("date"), "home": home.get("team", {}).get("displayName", ""),
                    "away": away.get("team", {}).get("displayName", ""),
                    "home_score": hs, "away_score": vs,
                }
        except (requests.RequestException, ValueError):
            errors += 1
    if not rows:
        raise ValueError("ESPN no devolvió resultados finalizados para esta temporada.")
    frame = pd.DataFrame(rows.values()).sort_values("date").reset_index(drop=True)
    return frame, errors
