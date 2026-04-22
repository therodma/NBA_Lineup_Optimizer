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
    "1979-80", "1980-81", "1981-82", "1982-83", "1983-84", "1984-85",
    "1985-86", "1986-87", "1987-88", "1988-89", "1989-90",
    "1990-91", "1991-92", "1992-93", "1993-94", "1994-95",
    "1995-96", "1996-97", "1997-98", "1998-99", "1999-00",
    "2000-01", "2001-02", "2002-03", "2003-04", "2004-05",
    "2005-06", "2006-07", "2007-08", "2008-09", "2009-10",
    "2010-11", "2011-12", "2012-13", "2013-14", "2014-15",
    "2015-16", "2016-17", "2017-18", "2018-19", "2019-20",
    "2020-21", "2021-22", "2022-23", "2023-24"
]

# Seasons where NBA.com advanced stats (ORTG/DRTG/BPM) are NOT available
NBA_API_UNAVAILABLE_BEFORE = "1996-97"

ERA_MAP = {
    **{s: "1980s" for s in ["1979-80","1980-81","1981-82","1982-83","1983-84",
                             "1984-85","1985-86","1986-87","1987-88","1988-89","1989-90"]},
    **{s: "1990s" for s in ["1990-91","1991-92","1992-93","1993-94","1994-95",
                             "1995-96","1996-97","1997-98","1998-99","1999-00"]},
    **{s: "2000s" for s in ["2000-01","2001-02","2002-03","2003-04","2004-05",
                             "2005-06","2006-07","2007-08","2008-09","2009-10"]},
    **{s: "2010s" for s in ["2010-11","2011-12","2012-13","2013-14","2014-15",
                             "2015-16","2016-17","2017-18","2018-19"]},
    **{s: "2020s" for s in ["2019-20","2020-21","2021-22","2022-23","2023-24"]},
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

    # Seasons before ~1996-97 are not available on NBA.com API — skip API, use BBRef only
    if season < NBA_API_UNAVAILABLE_BEFORE:
        return _fetch_bbref_season(season)

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
        return _fetch_bbref_season(season)  # fallback to BBRef

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

    df = df.drop_duplicates(subset=["PLAYER_ID"], keep="first")
    df["season"] = season
    df["_source"] = "nba_api"
    print(f"  [{season}] {len(df)} players")
    return df


def _fetch_bbref_season(season):
    """Fetch a season from Basketball Reference for pre-API eras."""
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from backend.scrapers.bbref_scraper import scrape_season_advanced, scrape_season_per36, merge_and_clean

    year = int(season.split("-")[0]) + 1
    try:
        adv = scrape_season_advanced(year)
        p36 = scrape_season_per36(year)
        if adv.empty or p36.empty:
            return pd.DataFrame()
        df = merge_and_clean(adv, p36)
        df["season"] = season
        df["_source"] = "bbref"
        print(f"  [{season}] {len(df)} players (BBRef)")
        return df
    except Exception as e:
        print(f"  [{season}] BBRef failed: {e}")
        return pd.DataFrame()


def build_players(df, season):
    players = []
    source = df.get("_source", pd.Series(["nba_api"] * len(df))).iloc[0] if len(df) > 0 else "nba_api"
    is_bbref = source == "bbref"

    for _, row in df.iterrows():
        min_val = float(row.get("MIN", row.get("minutes_per_game", 0)) or 0)
        if min_val < 5:
            continue

        ast = float(row.get("AST", row.get("assists", 0)) or 0)
        blk = float(row.get("BLK", row.get("blocks", 0)) or 0)
        reb = float(row.get("REB", row.get("rebounds", 0)) or 0)
        pts = float(row.get("PTS", row.get("points", 0)) or 0)
        fg3 = float(row.get("FG3_PCT", row.get("three_pt_pct", 0)) or 0)

        pos_group = str(row.get("POS_GROUP", "F"))
        pos = _assign_position(pos_group, ast, blk, reb, pts)
        flags = _role_flags(pos, ast, blk, fg3)
        ws    = float(row.get("W", row.get("win_shares", 0)) or 0)
        if not is_bbref:
            ws = ws * 0.12  # NBA API gives wins, not win shares
        min_val = max(min_val, 1)

        # Stats that may not exist for older seasons — store as None so frontend shows N/A
        off_rtg = row.get("OFF_RATING", row.get("offensive_rating", None))
        def_rtg = row.get("DEF_RATING", row.get("defensive_rating", None))
        net_rtg = row.get("NET_RATING", row.get("net_rating", None))
        ts      = row.get("TS_PCT", row.get("ts_pct", None))
        usg     = row.get("USG_PCT", row.get("usage_rate", None))
        bpm_val = row.get("bpm", None)
        per_val = row.get("PIE", row.get("per", None))

        off_rtg = float(off_rtg) if off_rtg is not None and str(off_rtg) != "nan" else None
        def_rtg = float(def_rtg) if def_rtg is not None and str(def_rtg) != "nan" else None
        net_rtg = float(net_rtg) if net_rtg is not None and str(net_rtg) != "nan" else None
        ts      = float(ts)      if ts      is not None and str(ts)      != "nan" else None
        usg     = float(usg)     if usg     is not None and str(usg)     != "nan" else None
        bpm_val = float(bpm_val) if bpm_val is not None and str(bpm_val) != "nan" else None
        per_val = float(per_val) if per_val is not None and str(per_val) != "nan" else None
        if per_val is not None and not is_bbref:
            per_val = per_val * 100  # NBA API PIE -> scale to PER range
        if bpm_val is None and net_rtg is not None:
            bpm_val = net_rtg * 0.25  # estimate BPM from net rating if missing

        players.append(Player(
            name             = str(row.get("PLAYER_NAME", row.get("name", ""))),
            position         = pos,
            height_inches    = int(float(row.get("PLAYER_HEIGHT_INCHES", row.get("height_inches", 0) or 0) or 0)) if str(row.get("PLAYER_HEIGHT_INCHES", row.get("height_inches", 0) or 0)) != "nan" else 0,
            era              = ERA_MAP.get(season, "2020s"),
            season           = season,
            team             = str(row.get("TEAM_ABBREVIATION", row.get("team", ""))),
            fg_pct           = float(row.get("FG_PCT", row.get("fg_pct", 0)) or 0),
            three_pt_pct     = fg3,
            ts_pct           = ts,
            offensive_rating = off_rtg,
            defensive_rating = def_rtg,
            net_rating       = net_rtg,
            rebounds         = reb,
            assists          = ast,
            blocks           = blk,
            steals           = float(row.get("STL", row.get("steals", 0)) or 0),
            points           = pts,
            turnovers        = float(row.get("TOV", row.get("turnovers", 0)) or 0),
            usage_rate       = (usg * 100) if usg is not None else None,
            win_shares       = ws if ws != 0 else None,
            win_shares_per48 = (ws / min_val * 48) if ws else None,
            bpm              = bpm_val,
            vorp             = float(row.get("vorp", 0) or 0),
            per              = per_val,
            games_played     = int(float(row.get("GP", row.get("games_played", 0)) or 0)),
            minutes_per_game = round(float(row.get("MIN", row.get("minutes_per_game", 0)) or 0) / max(int(float(row.get("GP", 1) or 1)), 1), 1),
            three_pt_attempts= int(float(row.get("FG3A", row.get("three_pt_attempts", 0)) or 0)),
            fg_attempts      = int(float(row.get("FGA", row.get("fg_attempts", 0)) or 0)),
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

    # Sequential fetching to avoid BBRef rate limiting (403s from parallel requests)
    for season in SEASONS:
        try:
            result = fetch_season_data(season)
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
