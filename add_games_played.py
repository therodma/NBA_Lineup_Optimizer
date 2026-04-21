"""
1. Adds games_played + minutes_per_game columns to existing DB
2. Fetches real GP and MIN/game from NBA.com for all seasons
3. Updates every player row
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
        # Add columns if they don't exist
        try:
            conn.execute(text("ALTER TABLE players ADD COLUMN games_played INTEGER DEFAULT 0"))
            conn.commit()
            print("  Added games_played column")
        except Exception:
            print("  games_played column already exists")
        try:
            conn.execute(text("ALTER TABLE players ADD COLUMN minutes_per_game FLOAT DEFAULT 0.0"))
            conn.commit()
            print("  Added minutes_per_game column")
        except Exception:
            print("  minutes_per_game column already exists")


def fetch_gp(season: str) -> pd.DataFrame:
    time.sleep(2)
    r = leaguedashplayerstats.LeagueDashPlayerStats(
        season=season,
        per_mode_detailed="PerGame",
        measure_type_detailed_defense="Base",
        season_type_all_star="Regular Season",
        timeout=60,
    )
    df = r.get_data_frames()[0]
    return df[["PLAYER_NAME", "GP", "MIN"]].copy()


def run():
    print("Step 1: Adding columns to DB...")
    add_columns()

    session = get_session()
    total_updated = 0

    for season in SEASONS:
        print(f"\n[{season}] Fetching GP data...")
        try:
            gp_df = fetch_gp(season)
        except Exception as e:
            print(f"  ERROR: {e}")
            continue

        # Build lookup: name -> (gp, min_per_game)
        gp_lookup = {}
        for _, row in gp_df.iterrows():
            name = str(row["PLAYER_NAME"])
            gp   = int(row.get("GP", 0) or 0)
            mpg  = float(row.get("MIN", 0) or 0)
            gp_lookup[name] = (gp, mpg)

        # Update players in DB for this season
        players = session.query(Player).filter(Player.season == season).all()
        updated = 0
        for p in players:
            if p.name in gp_lookup:
                gp, mpg = gp_lookup[p.name]
                p.games_played     = gp
                p.minutes_per_game = round(mpg, 1)
                updated += 1
            else:
                # Try to match unicode names by first+last name prefix
                matched = False
                for api_name, (gp, mpg) in gp_lookup.items():
                    pparts = (p.name or "").split()
                    aparts = api_name.split()
                    if (len(pparts) >= 2 and len(aparts) >= 2 and
                        pparts[0].lower() == aparts[0].lower() and
                        pparts[-1].lower()[:4] == aparts[-1].lower()[:4]):
                        p.games_played     = gp
                        p.minutes_per_game = round(mpg, 1)
                        updated += 1
                        matched = True
                        break
                if not matched:
                    p.games_played = 0

        session.commit()
        print(f"  Updated {updated}/{len(players)} players")
        total_updated += updated

    session.close()
    print(f"\nTotal updated: {total_updated}")

    # Verify
    print("\nVerifying GP for key players (2023-24):")
    session = get_session()
    for name in ["Stephen Curry", "Joel Embiid", "Jayson Tatum", "LeBron James",
                 "D.J. Wilson", "Drew Eubanks", "Luke Kornet", "Ryan Rollins"]:
        p = session.query(Player).filter(
            Player.name.ilike(f"%{name.split()[0]}%"),
            Player.season == "2023-24"
        ).first()
        if p:
            n = p.name.encode("ascii", "replace").decode()
            print(f"  {n:<28} GP={p.games_played:>3} MPG={p.minutes_per_game:>5.1f} 3pt={p.three_pt_pct*100:.1f}%")

    print("\nGP distribution 2023-24:")
    all_p = session.query(Player).filter(Player.season == "2023-24").all()
    buckets = {"GP=0": 0, "GP<20": 0, "GP<41": 0, "GP<60": 0, "GP<82": 0, "GP=82": 0}
    for p in all_p:
        gp = p.games_played or 0
        if gp == 0:       buckets["GP=0"] += 1
        elif gp < 20:     buckets["GP<20"] += 1
        elif gp < 41:     buckets["GP<41"] += 1
        elif gp < 60:     buckets["GP<60"] += 1
        elif gp < 82:     buckets["GP<82"] += 1
        else:             buckets["GP=82"] += 1
    for k, v in buckets.items():
        print(f"  {k}: {v} players")

    session.close()


if __name__ == "__main__":
    run()
