"""
Data pipeline — fetches by position group (G/F/C) for accurate positions.
Assigns PG/SG/SF/PF/C using assists + scoring profile within each group.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
from nba_api.stats.endpoints import leaguedashplayerstats, leaguedashplayerbiostats
from backend.models.database import get_session, init_db, Player
from sqlalchemy import text

SEASONS = [
    "2016-17", "2017-18", "2018-19", "2019-20",
    "2020-21", "2021-22", "2022-23", "2023-24"
]

ERA_MAP = {
    "2016-17": "2010s", "2017-18": "2010s", "2018-19": "2010s",
    "2019-20": "2020s", "2020-21": "2020s", "2021-22": "2020s",
    "2022-23": "2020s", "2023-24": "2020s",
}

# NBA.com position groups
POS_GROUPS = ["G", "F", "C"]


def _fetch_by_pos(season, pos_group, measure, per_mode, retries=3):
    for attempt in range(retries):
        try:
            time.sleep(0.8)
            r = leaguedashplayerstats.LeagueDashPlayerStats(
                season=season,
                per_mode_detailed=per_mode,
                measure_type_detailed_defense=measure,
                player_position_abbreviation_nullable=pos_group,
                season_type_all_star="Regular Season",
                timeout=60,
            )
            df = r.get_data_frames()[0]
            df["POS_GROUP"] = pos_group
            return df
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(3)
            else:
                print(f"    Warning [{season}][{pos_group}][{measure}]: {e}")
                return pd.DataFrame()


def _fetch_bios(season, retries=3):
    for attempt in range(retries):
        try:
            time.sleep(0.8)
            r = leaguedashplayerbiostats.LeagueDashPlayerBioStats(
                season=season,
                per_mode_simple="PerGame",
                season_type_all_star="Regular Season",
                timeout=60,
            )
            return r.get_data_frames()[0]
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(3)
            else:
                return pd.DataFrame()


def _assign_position(pos_group: str, ast: float, blk: float, reb: float, pts: float) -> str:
    """
    Assign specific position within group using stat profile.
    Guards (G):   high ast -> PG, else SG
    Forwards (F): high ast/pts -> SF, high reb/blk -> PF
    Centers (C):  always C
    """
    if pos_group == "G":
        return "PG" if ast >= 4.5 else "SG"
    elif pos_group == "F":
        return "SF" if (ast >= 2.0 or pts >= 15.0) and blk < 1.2 else "PF"
    else:
        return "C"


def _role_flags(pos, ast, blk, fg3):
    return {
        "is_ball_handler":           ("PG" in pos) or (ast >= 5.0),
        "is_rim_protector":          ("C" in pos and blk >= 1.5) or (blk >= 2.0),
        "is_three_point_specialist": fg3 >= 0.38,
    }


def fetch_season_data(season):
    print(f"  [{season}] fetching...")
    frames_base = []
    frames_adv  = []

    for pg in POS_GROUPS:
        b = _fetch_by_pos(season, pg, "Base", "Per36")
        a = _fetch_by_pos(season, pg, "Advanced", "PerGame")
        if not b.empty:
            frames_base.append(b)
        if not a.empty:
            frames_adv.append(a)

    if not frames_base:
        return pd.DataFrame()

    base = pd.concat(frames_base, ignore_index=True)
    adv  = pd.concat(frames_adv,  ignore_index=True) if frames_adv else pd.DataFrame()
    bio  = _fetch_bios(season)

    adv_keep = ["PLAYER_ID", "OFF_RATING", "DEF_RATING", "NET_RATING", "TS_PCT", "USG_PCT", "PIE"]
    bio_keep = ["PLAYER_ID", "PLAYER_HEIGHT_INCHES"]

    df = base
    if not adv.empty and all(c in adv.columns for c in adv_keep):
        df = df.merge(adv[adv_keep], on="PLAYER_ID", how="left")
    if not bio.empty and all(c in bio.columns for c in bio_keep):
        df = df.merge(bio[bio_keep], on="PLAYER_ID", how="left")

    # Remove duplicates (player on multiple teams)
    df = df.drop_duplicates(subset=["PLAYER_ID"], keep="first")
    df["season"] = season
    print(f"  [{season}] {len(df)} players")
    return df


def build_players(df, season):
    players = []
    for _, row in df.iterrows():
        if float(row.get("MIN", 0) or 0) < 5:
            continue

        ast = float(row.get("AST", 0) or 0)
        blk = float(row.get("BLK", 0) or 0)
        reb = float(row.get("REB", 0) or 0)
        pts = float(row.get("PTS", 0) or 0)
        fg3 = float(row.get("FG3_PCT", 0) or 0)

        pos_group = str(row.get("POS_GROUP", "F"))
        pos = _assign_position(pos_group, ast, blk, reb, pts)
        flags   = _role_flags(pos, ast, blk, fg3)
        ws      = float(row.get("W", 0) or 0) * 0.12
        min_val = max(float(row.get("MIN", 1) or 1), 1)

        players.append(Player(
            name             = str(row.get("PLAYER_NAME", "")),
            position         = pos,
            height_inches    = int(float(row.get("PLAYER_HEIGHT_INCHES", 0) or 0)),
            era              = ERA_MAP.get(season, "2020s"),
            season           = season,
            team             = str(row.get("TEAM_ABBREVIATION", "")),
            fg_pct           = float(row.get("FG_PCT", 0) or 0),
            three_pt_pct     = fg3,
            ts_pct           = float(row.get("TS_PCT", 0) or 0),
            offensive_rating = float(row.get("OFF_RATING", 110) or 110),
            defensive_rating = float(row.get("DEF_RATING", 110) or 110),
            net_rating       = float(row.get("NET_RATING", 0) or 0),
            rebounds         = reb,
            assists          = ast,
            blocks           = blk,
            steals           = float(row.get("STL", 0) or 0),
            points           = pts,
            turnovers        = float(row.get("TOV", 0) or 0),
            usage_rate       = float(row.get("USG_PCT", 0) or 0) * 100,
            win_shares       = ws,
            win_shares_per48 = ws / min_val * 48,
            bpm              = float(row.get("NET_RATING", 0) or 0) * 0.25,
            vorp             = 0.0,
            per              = float(row.get("PIE", 0) or 0) * 100,
            **flags
        ))
    return players


def run_pipeline():
    print("Initializing database...")
    init_db()

    session = get_session()
    session.execute(text("DELETE FROM players"))
    session.commit()
    session.close()
    print("Cleared existing data.\n")

    print(f"Fetching {len(SEASONS)} seasons (parallel, ~2 min)...\n")
    season_data = {}

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(fetch_season_data, s): s for s in SEASONS}
        for future in as_completed(futures):
            season = futures[future]
            try:
                result = future.result()
                if not result.empty:
                    season_data[season] = result
            except Exception as e:
                print(f"  [{season}] FAILED: {e}")

    print("\nLoading into database...")
    session = get_session()
    total = 0

    for season in SEASONS:
        if season not in season_data:
            continue
        players = build_players(season_data[season], season)
        for p in players:
            session.add(p)
        session.commit()
        print(f"  [{season}] {len(players)} players loaded")
        total += len(players)

    session.close()
    print(f"\nDone. {total} total players in database.")
    print("\nPosition breakdown:")
    session = get_session()
    for pos in ["PG", "SG", "SF", "PF", "C"]:
        count = session.query(Player).filter(Player.position == pos).count()
        print(f"  {pos}: {count}")
    session.close()


if __name__ == "__main__":
    run_pipeline()
