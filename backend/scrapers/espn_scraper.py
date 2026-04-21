import requests
import pandas as pd
import time
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from backend.config import SCRAPE_DELAY

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
ESPN_API = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"


def scrape_espn_roster(team_id: int) -> pd.DataFrame:
    """Fetch roster data for a team from ESPN public API."""
    time.sleep(SCRAPE_DELAY)
    url = f"{ESPN_API}/teams/{team_id}/roster"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    rows = []
    for group in data.get("athletes", []):
        for athlete in (group.get("items") or [group] if isinstance(group, dict) else []):
            rows.append({
                "name":     athlete.get("fullName", ""),
                "position": athlete.get("position", {}).get("abbreviation", ""),
                "height":   athlete.get("height", ""),
                "weight":   athlete.get("weight", ""),
                "jersey":   athlete.get("jersey", ""),
                "espn_id":  athlete.get("id", ""),
            })
    return pd.DataFrame(rows)


def scrape_all_espn_rosters() -> pd.DataFrame:
    """Scrape rosters for all 30 NBA teams."""
    # ESPN team IDs 1-30 cover all NBA franchises
    frames = []
    for team_id in range(1, 31):
        try:
            df = scrape_espn_roster(team_id)
            if not df.empty:
                frames.append(df)
                print(f"ESPN roster scraped: team {team_id}")
        except Exception as e:
            print(f"Error scraping ESPN team {team_id}: {e}")
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
