import requests
import pandas as pd
import time
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from backend.config import SCRAPE_DELAY

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Referer": "https://www.nba.com/",
    "Accept": "application/json",
    "x-nba-stats-origin": "stats",
    "x-nba-stats-token": "true",
}

BASE = "https://stats.nba.com/stats"


def _get(endpoint: str, params: dict) -> dict:
    time.sleep(SCRAPE_DELAY)
    resp = requests.get(f"{BASE}/{endpoint}", headers=HEADERS, params=params, timeout=20)
    resp.raise_for_status()
    return resp.json()


def _to_df(data: dict) -> pd.DataFrame:
    rs = data["resultSets"][0]
    return pd.DataFrame(rs["rowSet"], columns=rs["headers"])


def scrape_player_estimated_metrics(season: str = "2023-24") -> pd.DataFrame:
    """Fetch estimated offensive/defensive ratings from NBA.com."""
    data = _get("playerestimatedmetrics", {
        "Season": season,
        "SeasonType": "Regular Season",
    })
    df = _to_df(data)
    df["season"] = season
    return df[["PLAYER_NAME", "E_OFF_RATING", "E_DEF_RATING", "E_NET_RATING", "season"]].rename(columns={
        "PLAYER_NAME": "name",
        "E_OFF_RATING": "offensive_rating",
        "E_DEF_RATING": "defensive_rating",
        "E_NET_RATING": "net_rating",
    })


def scrape_player_hustle(season: str = "2023-24") -> pd.DataFrame:
    """Fetch hustle stats (deflections, contested shots, etc.)."""
    data = _get("playerhustlestats", {
        "Season": season,
        "SeasonType": "Regular Season",
        "PerMode": "PerGame",
    })
    df = _to_df(data)
    df["season"] = season
    keep = ["PLAYER_NAME", "CONTESTED_SHOTS", "DEFLECTIONS", "CHARGES_DRAWN", "season"]
    available = [c for c in keep if c in df.columns]
    return df[available].rename(columns={"PLAYER_NAME": "name"})


def scrape_nba_seasons(seasons: list) -> pd.DataFrame:
    """Scrape estimated metrics for multiple seasons."""
    frames = []
    for s in seasons:
        try:
            df = scrape_player_estimated_metrics(s)
            frames.append(df)
            print(f"NBA.com metrics scraped: {s}")
        except Exception as e:
            print(f"Error scraping NBA.com {s}: {e}")
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
