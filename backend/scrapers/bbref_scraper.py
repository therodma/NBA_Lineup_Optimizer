import requests
import pandas as pd
from bs4 import BeautifulSoup
import time
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from backend.config import SCRAPE_DELAY

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

BASE_URL = "https://www.basketball-reference.com"


def scrape_season_advanced(season_end_year: int) -> pd.DataFrame:
    """Scrape advanced stats table for a given season from Basketball Reference."""
    url = f"{BASE_URL}/leagues/NBA_{season_end_year}_advanced.html"
    print(f"Scraping advanced stats: {url}")
    time.sleep(SCRAPE_DELAY)

    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")
    table = soup.find("table", {"id": "advanced_stats"})
    if not table:
        print(f"No advanced table found for {season_end_year}")
        return pd.DataFrame()

    df = pd.read_html(str(table))[0]
    df = df[df["Rk"] != "Rk"].dropna(subset=["Player"])  # remove header rows
    df["season"] = f"{season_end_year - 1}-{str(season_end_year)[2:]}"
    return df


def scrape_season_per36(season_end_year: int) -> pd.DataFrame:
    """Scrape per-36-minute stats for a given season."""
    url = f"{BASE_URL}/leagues/NBA_{season_end_year}_per_minute.html"
    print(f"Scraping per-36 stats: {url}")
    time.sleep(SCRAPE_DELAY)

    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")
    table = soup.find("table", {"id": "per_minute_stats"})
    if not table:
        print(f"No per-36 table found for {season_end_year}")
        return pd.DataFrame()

    df = pd.read_html(str(table))[0]
    df = df[df["Rk"] != "Rk"].dropna(subset=["Player"])
    df["season"] = f"{season_end_year - 1}-{str(season_end_year)[2:]}"
    return df


def scrape_player_heights() -> pd.DataFrame:
    """Scrape player height/position from BBRef player index."""
    url = f"{BASE_URL}/players/"
    time.sleep(SCRAPE_DELAY)
    resp = requests.get(url, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(resp.text, "lxml")

    rows = []
    for letter_link in soup.select("ul.page_index li a"):
        letter_url = BASE_URL + letter_link["href"]
        time.sleep(SCRAPE_DELAY)
        r = requests.get(letter_url, headers=HEADERS, timeout=15)
        s = BeautifulSoup(r.text, "lxml")
        for row in s.select("table#players tbody tr"):
            cols = row.find_all("td")
            if len(cols) >= 4:
                name_tag = row.find("th")
                name = name_tag.text.strip() if name_tag else ""
                pos  = cols[0].text.strip()
                ht   = cols[1].text.strip()
                rows.append({"name": name, "position": pos, "height_str": ht})

    return pd.DataFrame(rows)


def height_to_inches(height_str: str) -> int:
    """Convert '6-7' format to total inches."""
    try:
        parts = height_str.split("-")
        return int(parts[0]) * 12 + int(parts[1])
    except Exception:
        return 0


def merge_and_clean(advanced: pd.DataFrame, per36: pd.DataFrame) -> pd.DataFrame:
    """Merge advanced and per-36 dataframes and normalize columns."""
    adv_cols = {
        "Player": "name", "Pos": "position", "Tm": "team",
        "PER": "per", "TS%": "ts_pct", "USG%": "usage_rate",
        "WS": "win_shares", "WS/48": "win_shares_per48",
        "BPM": "bpm", "VORP": "vorp", "season": "season"
    }
    per_cols = {
        "Player": "name", "Tm": "team",
        "FG%": "fg_pct", "3P%": "three_pt_pct",
        "TRB": "rebounds", "AST": "assists",
        "BLK": "blocks", "STL": "steals",
        "PTS": "points", "TOV": "turnovers", "season": "season"
    }

    adv = advanced.rename(columns=adv_cols)[[c for c in adv_cols.values() if c in advanced.rename(columns=adv_cols).columns]]
    p36 = per36.rename(columns=per_cols)[[c for c in per_cols.values() if c in per36.rename(columns=per_cols).columns]]

    merged = pd.merge(adv, p36, on=["name", "team", "season"], how="left")

    # Keep only one row per player per season (best team if traded)
    merged = merged[merged["team"] != "TOT"]
    merged = merged.drop_duplicates(subset=["name", "season"])

    numeric_cols = ["per", "ts_pct", "usage_rate", "win_shares", "win_shares_per48",
                    "bpm", "vorp", "fg_pct", "three_pt_pct", "rebounds",
                    "assists", "blocks", "steals", "points", "turnovers"]
    for col in numeric_cols:
        if col in merged.columns:
            merged[col] = pd.to_numeric(merged[col], errors="coerce")

    return merged


def scrape_seasons(start_year: int = 2015, end_year: int = 2024) -> pd.DataFrame:
    """Scrape multiple seasons and return combined DataFrame."""
    all_frames = []
    for year in range(start_year, end_year + 1):
        try:
            adv = scrape_season_advanced(year)
            p36 = scrape_season_per36(year)
            if not adv.empty and not p36.empty:
                merged = merge_and_clean(adv, p36)
                all_frames.append(merged)
        except Exception as e:
            print(f"Error scraping {year}: {e}")
    return pd.concat(all_frames, ignore_index=True) if all_frames else pd.DataFrame()
