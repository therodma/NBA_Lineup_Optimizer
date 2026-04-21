"""
Adds fg_attempts, three_pt_attempts, ft_attempts to DB
and populates from NBA.com season totals for all seasons.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import time
import pandas as pd
from nba_api.stats.endpoints import leaguedashplayerstats
from backend.models.database import get_session, get_engine, Player
from sqlalchemy import text

SEASONS = [
    "2016-17", "2017-18", "2018-19", "2019-20",
    "2020-21", "2021-22", "2022-23", "2023-24"
]


def add_columns():
    engine = get_engine()
    with engine.connect() as conn:
        for col, typedef in [
            ("fg_attempts",       "INTEGER DEFAULT 0"),
            ("three_pt_attempts", "INTEGER DEFAULT 0"),
            ("ft_attempts",       "INTEGER DEFAULT 0"),
        ]:
            try:
                conn.execute(text(f"ALTER TABLE players ADD COLUMN {col} {typedef}"))
                conn.commit()
                print(f"  Added {col}")
            except Exception:
                print(f"  {col} already exists")


def fetch_totals(season: str) -> pd.DataFrame:
    for attempt in range(3):
        try:
            time.sleep(2)
            r = leaguedashplayerstats.LeagueDashPlayerStats(
                season=season,
                per_mode_detailed="Totals",
                measure_type_detailed_defense="Base",
                season_type_all_star="Regular Season",
                timeout=60,
            )
            df = r.get_data_frames()[0]
            return df[["PLAYER_NAME", "FGA", "FG3A", "FTA"]].copy()
        except Exception as e:
            if attempt < 2:
                time.sleep(5)
            else:
                print(f"  ERROR fetching {season}: {e}")
                return pd.DataFrame()


def run():
    print("Adding columns...")
    add_columns()

    session = get_session()
    total_updated = 0

    for season in SEASONS:
        print(f"[{season}] fetching totals...")
        df = fetch_totals(season)
        if df.empty:
            continue

        lookup = {}
        for _, row in df.iterrows():
            lookup[str(row["PLAYER_NAME"])] = (
                int(row.get("FGA", 0) or 0),
                int(row.get("FG3A", 0) or 0),
                int(row.get("FTA", 0) or 0),
            )

        players = session.query(Player).filter(Player.season == season).all()
        updated = 0
        for p in players:
            data = lookup.get(p.name)
            if not data:
                # Unicode name fallback
                for api_name, vals in lookup.items():
                    pparts = (p.name or "").split()
                    aparts = api_name.split()
                    if (len(pparts) >= 2 and len(aparts) >= 2 and
                        pparts[0].lower() == aparts[0].lower() and
                        pparts[-1].lower()[:4] == aparts[-1].lower()[:4]):
                        data = vals
                        break
            if data:
                p.fg_attempts, p.three_pt_attempts, p.ft_attempts = data
                updated += 1

        session.commit()
        print(f"  Updated {updated}/{len(players)} players")
        total_updated += updated

    session.close()
    print(f"\nTotal: {total_updated} players updated")

    # Verify
    print("\nVerification — 2023-24 shooting outliers:")
    session = get_session()
    outliers = session.query(Player).filter(
        Player.season == "2023-24",
        Player.three_pt_pct >= 0.45,
        Player.three_pt_attempts < 30,
        Player.games_played >= 30
    ).order_by(Player.three_pt_pct.desc()).all()
    print(f"  Players with 45%+ 3PT but < 30 attempts: {len(outliers)}")
    for p in outliers[:8]:
        n = p.name.encode("ascii","replace").decode()
        print(f"    {n:<28} 3pt={p.three_pt_pct*100:.1f}% att={p.three_pt_attempts} gp={p.games_played}")

    print("\nLegit shooters (45%+ 3PT, 100+ attempts):")
    legit = session.query(Player).filter(
        Player.season == "2023-24",
        Player.three_pt_pct >= 0.40,
        Player.three_pt_attempts >= 100,
        Player.games_played >= 30
    ).order_by(Player.three_pt_pct.desc()).limit(10).all()
    for p in legit:
        n = p.name.encode("ascii","replace").decode()
        print(f"    {n:<28} 3pt={p.three_pt_pct*100:.1f}% att={p.three_pt_attempts} gp={p.games_played}")

    session.close()


if __name__ == "__main__":
    run()
