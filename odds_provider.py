"""TheOddsAPI adapter. Requires a user-supplied API key; never hardcode credentials."""
import requests
import pandas as pd

SPORTS = {"NFL": "americanfootball_nfl", "NCAAF": "americanfootball_ncaaf"}
MARKETS = {"h2h": "ML", "spreads": "Spread", "totals": "Total"}

def fetch_odds(league, api_key):
    if league not in SPORTS:
        raise ValueError("Unsupported league")
    if not api_key:
        raise ValueError("Missing API key")
    response = requests.get(f"https://api.the-odds-api.com/v4/sports/{SPORTS[league]}/odds/",
                            params={"markets": "h2h,spreads,totals",
                                    "regions": "us", "oddsFormat": "american", "apiKey": api_key},
                            headers={"x-api-key": api_key}, timeout=15)
    response.raise_for_status()
    rows = []
    for event in response.json():
        for book in event.get("bookmakers", []):
            for market in book.get("markets", []):
                for outcome in market.get("outcomes", []):
                    rows.append({
                        "Liga": league, "Inicio UTC": event.get("start_time", event.get("commence_time")),
                        "Partido": f'{event.get("away_team", "")} @ {event.get("home_team", "")}',
                        "Casa": book.get("title", book.get("key", "")),
                        "Mercado": MARKETS.get(market.get("key"), market.get("key")),
                        "Selección": outcome.get("name"), "Línea": outcome.get("point"),
                        "Momio americano": outcome.get("price"),
                        "Actualizado UTC": book.get("last_update", market.get("last_update", "")),
                    })
    return pd.DataFrame(rows)
