"""
For each player:
1. Fetches GP at each position group (G, F, C) from NBA.com
2. Determines primary position group = group with most GP (min 30)
3. Assigns specific position (PG/SG/SF/PF/C) within that group
4. Assigns secondary position from the other group if GP >= 30 there too
5. Updates position_group and secondary_position in DB
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

MIN_GP = 30  # minimum games to qualify at a position group


def add_columns():
    engine = get_engine()
    with engine.connect() as conn:
        for col, typedef in [
            ("position_group",    "TEXT DEFAULT ''"),
            ("secondary_position","TEXT DEFAULT ''"),
        ]:
            try:
                conn.execute(text(f"ALTER TABLE players ADD COLUMN {col} {typedef}"))
                conn.commit()
                print(f"  Added {col}")
            except Exception:
                print(f"  {col} already exists")


def fetch_group(season: str, group: str) -> pd.DataFrame:
    for attempt in range(3):
        try:
            time.sleep(2.0)
            r = leaguedashplayerstats.LeagueDashPlayerStats(
                season=season,
                per_mode_detailed="PerGame",
                measure_type_detailed_defense="Base",
                player_position_abbreviation_nullable=group,
                season_type_all_star="Regular Season",
                timeout=60,
            )
            df = r.get_data_frames()[0][["PLAYER_NAME", "GP", "MIN", "AST", "BLK", "REB", "PTS"]].copy()
            df["group"] = group
            return df
        except Exception as e:
            if attempt < 2:
                time.sleep(5)
            else:
                raise e


def _specific_position(group: str, ast: float, blk: float, reb: float, pts: float) -> str:
    """Assign PG/SG/SF/PF/C within a position group using stat profile."""
    if group == "G":
        # PG: primary ball handlers with high assists
        return "PG" if ast >= 5.0 else "SG"
    elif group == "F":
        # PF: high rebounders/shot blockers; SF: scorers/playmakers
        if blk >= 1.0 and reb >= 7.0:  return "PF"
        if reb >= 8.0:                  return "PF"
        if ast >= 3.5 and pts >= 18.0:  return "SF"  # wing scorer
        if pts >= 20.0:                 return "SF"  # high scorer = SF
        if blk >= 0.8 and reb >= 6.0:  return "PF"
        return "SF"
    else:  # C
        return "C"


def _secondary_specific(primary_group: str, secondary_group: str,
                         ast: float, blk: float, reb: float, pts: float) -> str:
    """Assign specific secondary position."""
    return _specific_position(secondary_group, ast, blk, reb, pts)


def process_season(season: str, session) -> int:
    print(f"  [{season}] fetching G/F/C groups...")
    try:
        g_df = fetch_group(season, "G")
        f_df = fetch_group(season, "F")
        c_df = fetch_group(season, "C")
    except Exception as e:
        print(f"  [{season}] ERROR: {e}")
        return 0

    # Build per-player GP lookup per group
    # {name: {group: (gp, ast, blk, reb, pts)}}
    player_groups = {}

    for df in [g_df, f_df, c_df]:
        for _, row in df.iterrows():
            name  = str(row["PLAYER_NAME"])
            group = str(row["group"])
            gp    = int(row.get("GP", 0) or 0)
            ast   = float(row.get("AST", 0) or 0)
            blk   = float(row.get("BLK", 0) or 0)
            reb   = float(row.get("REB", 0) or 0)
            pts   = float(row.get("PTS", 0) or 0)
            if name not in player_groups:
                player_groups[name] = {}
            player_groups[name][group] = (gp, ast, blk, reb, pts)

    updated = 0
    players = session.query(Player).filter(Player.season == season).all()

    for p in players:
        # Try exact name match first, then unicode-safe prefix match
        groups = player_groups.get(p.name)
        if not groups:
            for api_name, grps in player_groups.items():
                pparts = (p.name or "").split()
                aparts = api_name.split()
                if (len(pparts) >= 2 and len(aparts) >= 2 and
                    pparts[0].lower() == aparts[0].lower() and
                    pparts[-1].lower()[:4] == aparts[-1].lower()[:4]):
                    groups = grps
                    break

        if not groups:
            continue

        # Find all groups where player has >= MIN_GP
        qualified = {g: data for g, data in groups.items() if data[0] >= MIN_GP}

        if not qualified:
            # Use whichever group they have most GP in, even if < 30
            if groups:
                primary_group = max(groups, key=lambda g: groups[g][0])
                gp, ast, blk, reb, pts = groups[primary_group]
                p.position_group    = primary_group
                p.position          = _specific_position(primary_group, ast, blk, reb, pts)
                p.secondary_position = ""
                updated += 1
            continue

        # Primary = group with most GP among qualified
        primary_group = max(qualified, key=lambda g: qualified[g][0])
        gp, ast, blk, reb, pts = qualified[primary_group]

        primary_pos = _specific_position(primary_group, ast, blk, reb, pts)

        # Secondary = other qualified group(s), pick the one with most GP
        secondary_groups = {g: d for g, d in qualified.items() if g != primary_group}
        if secondary_groups:
            sec_group = max(secondary_groups, key=lambda g: secondary_groups[g][0])
            sec_gp, sec_ast, sec_blk, sec_reb, sec_pts = secondary_groups[sec_group]
            secondary_pos = _secondary_specific(
                primary_group, sec_group, sec_ast, sec_blk, sec_reb, sec_pts
            )
        else:
            secondary_pos = ""

        p.position_group     = primary_group
        p.position           = primary_pos
        p.secondary_position = secondary_pos
        updated += 1

    session.commit()
    return updated


def run():
    print("Step 1: Adding columns...")
    add_columns()

    session = get_session()
    total = 0

    for season in SEASONS:
        n = process_season(season, session)
        print(f"  [{season}] updated {n} players")
        total += n

    session.close()
    print(f"\nTotal updated: {total}")

    # Verify
    print("\nKey player position verification (2023-24):")
    session = get_session()
    checks = [
        "Stephen Curry", "LeBron James", "Giannis Antetokounmpo",
        "Joel Embiid", "Jayson Tatum", "Kevin Durant",
        "Draymond Green", "Anthony Davis", "Luka Don",
        "Shai Gilgeous", "James Harden", "Damian Lillard"
    ]
    print(f"{'Name':<28} {'Pos':<4} {'SecPos':<6} {'Group':<6} {'GP':>4}")
    print("-" * 55)
    for name in checks:
        p = session.query(Player).filter(
            Player.name.ilike(f"%{name.split()[0]}%"),
            Player.season == "2023-24"
        ).first()
        if p:
            n = p.name.encode("ascii", "replace").decode()
            print(f"  {n:<26} {p.position:<4} {p.secondary_position or '-':<6} {p.position_group:<6} {p.games_played:>4}")

    print("\nDual-position players (2023-24, GP>=30 at both):")
    dual = session.query(Player).filter(
        Player.season == "2023-24",
        Player.secondary_position != "",
        Player.secondary_position != None,
        Player.games_played >= 30
    ).limit(15).all()
    for p in dual:
        n = p.name.encode("ascii", "replace").decode()
        print(f"  {n:<28} primary={p.position} secondary={p.secondary_position} group={p.position_group}")

    session.close()


if __name__ == "__main__":
    run()
