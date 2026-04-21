import pandas as pd
import numpy as np
from typing import Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.models.database import get_session, Player

LINEUP_SLOTS = {
    "best_shooting":  ["PG", "SG", "SF", "PF", "C"],
    "best_offense":   ["PG", "SG", "SF", "PF", "C"],
    "best_defense":   ["PG", "SG", "SF", "PF", "C"],
    "most_balanced":  ["PG", "SG", "SF", "PF", "C"],
    "small_ball":     ["PG", "SG", "SF", "SF", "PF"],
    "traditional":    ["PG", "SG", "SF", "PF", "C"],
}

LINEUP_WEIGHTS = {
    # Each lineup type has its primary focus weights PLUS a baseline
    # winning contribution component (bpm, net_rating, win_shares).
    # This ensures players who are statistically good at the filter
    # but are net negatives on the court don't make the lineup
    # unless they're genuinely the best available option.
    "best_shooting": {
        "three_pt_pct":    0.35,
        "ts_pct":          0.20,
        "fg_pct":          0.15,
        "offensive_rating": 0.10,
        # Winning floor
        "bpm":             0.10,
        "win_shares":      0.05,
        "net_rating":      0.05,
    },
    "best_offense": {
        "offensive_rating": 0.25,
        "ts_pct":           0.20,
        "points":           0.15,
        "assists":          0.10,
        "per":              0.10,
        # Winning floor
        "bpm":              0.10,
        "win_shares":       0.05,
        "net_rating":       0.05,
    },
    "best_defense": {
        "defensive_rating": -0.30,
        "blocks":           0.20,
        "steals":           0.20,
        "rebounds":         0.10,
        # Winning floor
        "bpm":              0.10,
        "win_shares":       0.05,
        "net_rating":       0.05,
    },
    "most_balanced": {
        "per":              0.18,
        "bpm":              0.18,
        "offensive_rating": 0.12,
        "defensive_rating": -0.12,
        "win_shares":       0.15,
        "net_rating":       0.10,
        "rebounds":         0.08,
        "assists":          0.07,
    },
    "small_ball": {
        "three_pt_pct":    0.20,
        "offensive_rating": 0.20,
        "assists":          0.15,
        "steals":           0.10,
        "ts_pct":           0.10,
        # Winning floor
        "bpm":              0.10,
        "win_shares":       0.05,
        "net_rating":       0.10,
    },
    "traditional": {
        "rebounds":         0.22,
        "blocks":           0.18,
        "defensive_rating": -0.18,
        "win_shares":       0.15,
        "per":              0.12,
        # Winning floor
        "bpm":              0.08,
        "net_rating":       0.07,
    },
}

LINEUP_DESCRIPTIONS = {
    "best_shooting":  "maximizing three-point percentage, true shooting, and spacing",
    "best_offense":   "maximizing offensive rating, scoring efficiency, and playmaking",
    "best_defense":   "minimizing defensive rating while maximizing blocks, steals, and rebounding",
    "most_balanced":  "optimizing two-way impact using PER, BPM, win shares, and net rating",
    "small_ball":     "prioritizing floor spacing, ball movement, and perimeter defense without a traditional center",
    "traditional":    "emphasizing rebounding, rim protection, and interior dominance",
}

KEY_STAT_LABELS = {
    "best_shooting":  ("3PT%", "three_pt_pct", lambda v: f"{v*100:.1f}%"),
    "best_offense":   ("ORTG", "offensive_rating", lambda v: f"{v:.1f}"),
    "best_defense":   ("DRTG", "defensive_rating", lambda v: f"{v:.1f}"),
    "most_balanced":  ("PER",  "per",              lambda v: f"{v:.1f}"),
    "small_ball":     ("ORTG", "offensive_rating", lambda v: f"{v:.1f}"),
    "traditional":    ("REB",  "rebounds",         lambda v: f"{v:.1f}"),
}


def _query_players(session, era, season, min_height, max_height, positions) -> pd.DataFrame:
    q = session.query(Player)
    if era:
        q = q.filter(Player.era == era)
    if season:
        q = q.filter(Player.season == season)
    if min_height:
        q = q.filter(Player.height_inches >= min_height)
    if max_height:
        q = q.filter(Player.height_inches <= max_height)
    if positions:
        q = q.filter(Player.position.in_(positions))

    rows = q.all()
    if not rows:
        return pd.DataFrame()

    return pd.DataFrame([{
        "id": p.id, "name": p.name, "position": p.position,
        "height_inches": p.height_inches, "era": p.era, "season": p.season,
        "team": p.team, "fg_pct": p.fg_pct or 0, "three_pt_pct": p.three_pt_pct or 0,
        "ts_pct": p.ts_pct or 0, "offensive_rating": p.offensive_rating or 110,
        "defensive_rating": p.defensive_rating or 110, "net_rating": p.net_rating or 0,
        "rebounds": p.rebounds or 0, "assists": p.assists or 0, "blocks": p.blocks or 0,
        "steals": p.steals or 0, "points": p.points or 0, "turnovers": p.turnovers or 0,
        "usage_rate": p.usage_rate or 0, "win_shares": p.win_shares or 0,
        "win_shares_per48": p.win_shares_per48 or 0, "bpm": p.bpm or 0,
        "vorp": p.vorp or 0, "per": p.per or 0,
        "is_ball_handler": bool(p.is_ball_handler),
        "is_rim_protector": bool(p.is_rim_protector),
        "is_three_point_specialist": bool(p.is_three_point_specialist),
        "games_played": p.games_played or 0,
        "minutes_per_game": p.minutes_per_game or 0.0,
        "position_group": p.position_group or "",
        "secondary_position": p.secondary_position or "",
        "fg_attempts": p.fg_attempts or 0,
        "three_pt_attempts": p.three_pt_attempts or 0,
        "ft_attempts": p.ft_attempts or 0,
    } for p in rows])


def _score(row: dict, weights: dict, maxvals: dict) -> float:
    """
    Score a player using normalized stats.
    Handles both positive weights (higher = better) and
    negative weights (lower = better, e.g. defensive_rating).
    For negative weights: score += |w| * (1 - val/max) so lower values score higher.
    """
    score = 0.0
    for col, w in weights.items():
        val = float(row.get(col, 0) or 0)
        mx  = maxvals.get(col, 1) or 1
        if w < 0:
            # Lower is better: invert so best (lowest) value scores highest
            mn = maxvals.get(f"{col}_min", 0)
            rng = mx - mn
            if rng > 0:
                score += abs(w) * (1.0 - (val - mn) / rng)
            else:
                score += abs(w)
        else:
            score += w * (val / mx)
    return score


def _get_top_for_pos(df: pd.DataFrame, pos: str, weights: dict, maxvals: dict,
                     exclude_ids: set) -> list:
    """
    For a given position slot:
    1. Score ALL primary players at this position (position == pos, GP >= 30)
    2. Score ALL secondary players at this position (secondary_position == pos, GP >= 30)
    3. Merge both pools and sort by score — best player wins regardless of primary/secondary
    4. Fallback to adjacent positions only if both pools are empty

    A player's score is always based on the lineup filter weights (e.g. 3PT% for shooting),
    so a secondary SG who shoots better than every primary SG will rank above them.
    """
    qualified = df[df["games_played"] >= 30].copy()
    available = qualified[~qualified["id"].isin(exclude_ids)]

    # Pool 1: primary position players
    primary = available[available["position"] == pos].copy()

    # Pool 2: secondary position players (played 30+ games at this pos as secondary)
    secondary = available[
        (available["secondary_position"] == pos) &
        (available["position"] != pos)  # don't double-count
    ].copy()

    # Score each pool independently using the same weights
    if not primary.empty:
        primary["_score"]    = primary.apply(lambda r: _score(r.to_dict(), weights, maxvals), axis=1)
        primary["_tier"]     = "primary"

    if not secondary.empty:
        secondary["_score"]  = secondary.apply(lambda r: _score(r.to_dict(), weights, maxvals), axis=1)
        secondary["_tier"]   = "secondary"

    # Merge and sort purely by score — best player wins
    frames = [f for f in [primary, secondary] if not f.empty]
    if frames:
        combined = pd.concat(frames, ignore_index=True)
        combined = combined.sort_values("_score", ascending=False)
        return combined.to_dict("records")

    # Fallback: adjacent positions — only if player has secondary_position matching
    fallback_map = {
        "PG": ["SG"], "SG": ["PG", "SF"],
        "SF": ["SG", "PF"], "PF": ["SF", "C"], "C": ["PF"]
    }
    for alt in fallback_map.get(pos, []):
        # Only pull players whose secondary_position explicitly matches the needed slot
        alt_df = available[
            (available["position"] == alt) &
            (available["secondary_position"] == pos)
        ].copy()
        if not alt_df.empty:
            alt_df["_score"] = alt_df.apply(lambda r: _score(r.to_dict(), weights, maxvals), axis=1)
            alt_df["_tier"]  = "fallback"
            return alt_df.sort_values("_score", ascending=False).to_dict("records")

    # Last resort: any available player at adjacent position regardless of secondary
    for alt in fallback_map.get(pos, []):
        alt_df = available[available["position"] == alt].copy()
        if not alt_df.empty:
            alt_df["_score"] = alt_df.apply(lambda r: _score(r.to_dict(), weights, maxvals), axis=1)
            alt_df["_tier"]  = "last_resort"
            return alt_df.sort_values("_score", ascending=False).to_dict("records")

    return []


def _notable_snubs(df: pd.DataFrame, pos: str, picked: dict,
                   weights: dict, maxvals: dict, lineup_type: str) -> list:
    """
    Find players (primary OR secondary at this position) who scored highly
    but weren't picked, and explain why.
    """
    # Include both primary and secondary candidates for this position
    primary   = df[df["position"] == pos].copy()
    secondary = df[
        (df["secondary_position"] == pos) & (df["position"] != pos)
    ].copy()

    frames = [f for f in [primary, secondary] if not f.empty]
    if not frames:
        return []

    pos_df = pd.concat(frames, ignore_index=True).drop_duplicates(subset=["id"])
    pos_df["_score"] = pos_df.apply(lambda r: _score(r.to_dict(), weights, maxvals), axis=1)
    top20 = pos_df.nlargest(20, "_score").to_dict("records")

    snubs = []
    picked_name  = picked.get("name", "")
    picked_score = picked.get("_score", 0)
    stat_label, stat_key, stat_fmt = KEY_STAT_LABELS[lineup_type]

    for p in top20:
        if p["name"] == picked_name:
            continue
        if p["_score"] < picked_score * 0.85:
            break
        reason = _snub_reason(p, picked, lineup_type, stat_key)
        if reason:
            tier = "primary" if p.get("position") == pos else "secondary"
            snubs.append({
                "name":   p["name"],
                "season": p["season"],
                "stat":   stat_fmt(float(p.get(stat_key, 0) or 0)),
                "reason": reason,
                "tier":   tier,
            })
        if len(snubs) >= 2:
            break

    return snubs


def _snub_reason(snub: dict, winner: dict, lineup_type: str, stat_key: str) -> str:
    """Generate a plain-English reason why this player was not picked over the winner."""
    sn = snub["name"]
    wn = winner["name"]
    sv = float(snub.get(stat_key, 0) or 0)
    wv = float(winner.get(stat_key, 0) or 0)

    if lineup_type == "best_shooting":
        if snub.get("three_pt_pct", 0) < winner.get("three_pt_pct", 0):
            return (f"{sn} ({snub['three_pt_pct']*100:.1f}% from three) shot worse "
                    f"than {wn} ({winner['three_pt_pct']*100:.1f}%) despite similar efficiency.")
        if snub.get("ts_pct", 0) < winner.get("ts_pct", 0) - 0.03:
            return (f"{sn} had a lower true shooting % ({snub['ts_pct']*100:.1f}%) "
                    f"compared to {wn} ({winner['ts_pct']*100:.1f}%).")

    elif lineup_type == "best_offense":
        if snub.get("offensive_rating", 0) < winner.get("offensive_rating", 0) - 2:
            return (f"{sn} had a lower offensive rating ({snub['offensive_rating']:.1f}) "
                    f"than {wn} ({winner['offensive_rating']:.1f}).")
        if snub.get("ts_pct", 0) < winner.get("ts_pct", 0) - 0.03:
            return (f"{sn} was less efficient (TS% {snub['ts_pct']*100:.1f}%) "
                    f"than {wn} (TS% {winner['ts_pct']*100:.1f}%).")

    elif lineup_type == "best_defense":
        if snub.get("defensive_rating", 999) > winner.get("defensive_rating", 999) + 2:
            return (f"{sn} had a higher (worse) defensive rating ({snub['defensive_rating']:.1f}) "
                    f"than {wn} ({winner['defensive_rating']:.1f}).")

    elif lineup_type == "most_balanced":
        if snub.get("per", 0) < winner.get("per", 0) - 1:
            return (f"{sn} had a lower PER ({snub['per']:.1f}) than {wn} ({winner['per']:.1f}), "
                    f"indicating less overall two-way impact.")

    elif lineup_type == "traditional":
        if snub.get("rebounds", 0) < winner.get("rebounds", 0) - 1:
            return (f"{sn} rebounded less ({snub['rebounds']:.1f}/36) "
                    f"than {wn} ({winner['rebounds']:.1f}/36).")

    # Generic fallback
    return (f"{sn} scored slightly lower overall in the {lineup_type.replace('_',' ')} "
            f"metric weighting for this position.")


def _player_reason(player: dict, pos: str, weights: dict, maxvals: dict,
                   lineup_type: str, pick_order: int) -> str:
    """Generate a plain-English reason why this player was selected."""
    name = player["name"]
    stat_label, stat_key, stat_fmt = KEY_STAT_LABELS[lineup_type]
    stat_val = stat_fmt(float(player.get(stat_key, 0) or 0))

    ordinals = ["first", "second", "third", "fourth", "fifth"]
    order_str = ordinals[pick_order] if pick_order < 5 else f"#{pick_order+1}"

    pos_names = {"PG": "point guard", "SG": "shooting guard", "SF": "small forward",
                 "PF": "power forward", "C": "center"}
    pos_name = pos_names.get(pos, pos)

    if lineup_type == "best_shooting":
        return (f"Selected {order_str} as the {pos_name}. {name} led this position "
                f"with a {stat_val} {stat_label} and a true shooting of "
                f"{player['ts_pct']*100:.1f}%, making them the most efficient shooter "
                f"at this spot in the dataset.")

    elif lineup_type == "best_offense":
        return (f"Selected {order_str} as the {pos_name}. {name} posted an offensive "
                f"rating of {player['offensive_rating']:.1f} with {player['points']:.1f} "
                f"points and {player['assists']:.1f} assists per 36 minutes, ranking "
                f"highest at this position for offensive output.")

    elif lineup_type == "best_defense":
        return (f"Selected {order_str} as the {pos_name}. {name} had a defensive "
                f"rating of {player['defensive_rating']:.1f} with {player['blocks']:.1f} "
                f"blocks and {player['steals']:.1f} steals per 36, the best defensive "
                f"profile at this position.")

    elif lineup_type == "most_balanced":
        return (f"Selected {order_str} as the {pos_name}. {name} had a PER of "
                f"{player['per']:.1f} and BPM of {player['bpm']:.2f}, reflecting "
                f"elite two-way impact. Their win shares ({player['win_shares']:.1f}) "
                f"confirm consistent value on both ends.")

    elif lineup_type == "small_ball":
        return (f"Selected {order_str} as the {pos_name} in this positionless lineup. "
                f"{name} provides floor spacing ({player['three_pt_pct']*100:.1f}% from three) "
                f"and offensive creation ({player['offensive_rating']:.1f} ORTG), fitting "
                f"the pace-and-space system.")

    elif lineup_type == "traditional":
        return (f"Selected {order_str} as the {pos_name}. {name} brings "
                f"{player['rebounds']:.1f} rebounds and {player['blocks']:.1f} blocks "
                f"per 36 minutes, anchoring the traditional frontcourt with size and "
                f"interior presence.")

    return f"Selected {order_str} as the {pos_name} based on overall fit for this lineup type."


def _build_lineup_summary(lineup: list, lineup_type: str, snubs_by_pos: dict,
                          df: pd.DataFrame, weights: dict, maxvals: dict) -> dict:
    """Build the full summary object for the lineup."""
    pos_names = {"PG": "Point Guard", "SG": "Shooting Guard", "SF": "Small Forward",
                 "PF": "Power Forward", "C": "Center"}

    desc = LINEUP_DESCRIPTIONS[lineup_type]
    stat_label, stat_key, stat_fmt = KEY_STAT_LABELS[lineup_type]

    # Overall lineup summary
    avg_stat = float(np.mean([p.get(stat_key, 0) for p in lineup]))
    overall = (
        f"This {lineup_type.replace('_', ' ')} lineup was built by {desc}. "
        f"The five players were selected position-by-position — the best available "
        f"at each spot was chosen first, with each subsequent pick required to fill "
        f"a different position. No player appears twice. "
        f"The combined {stat_label} across the lineup averages {stat_fmt(avg_stat)}, "
        f"with a projected net rating of "
        f"{np.mean([p.get('net_rating',0) for p in lineup]):.1f}."
    )

    # Per-player explanations
    player_explanations = []
    for i, p in enumerate(lineup):
        explanation = {
            "name":   p["name"],
            "reason": _player_reason(p, p["position"], weights, maxvals, lineup_type, i),
            "snubs":  snubs_by_pos.get(p["position"], []),
        }
        player_explanations.append(explanation)

    # Synergy note
    three_shooters = sum(1 for p in lineup if p.get("three_pt_pct", 0) >= 0.36)
    has_handler    = any(p.get("is_ball_handler") for p in lineup)
    has_rim        = any(p.get("is_rim_protector") for p in lineup)
    total_reb      = sum(p.get("rebounds", 0) for p in lineup)

    synergy_notes = []
    if three_shooters >= 3:
        synergy_notes.append(f"{three_shooters} players shoot 36%+ from three, creating elite floor spacing.")
    if has_handler:
        synergy_notes.append("The lineup includes a primary ball handler to run the offense.")
    if has_rim:
        synergy_notes.append("Rim protection is present, providing defensive insurance.")
    if total_reb >= 30:
        synergy_notes.append(f"Combined rebounding of {total_reb:.1f} per 36 gives this lineup strong board control.")
    if not synergy_notes:
        synergy_notes.append("This lineup prioritizes individual excellence at each position over role-based synergy.")

    return {
        "overall":      overall,
        "players":      player_explanations,
        "synergy":      " ".join(synergy_notes),
    }


def _predict_win_pct(lineup: list) -> float:
    avg_net = np.mean([p.get("net_rating", 0) for p in lineup])
    wins = max(10, min(75, 41 + avg_net * 4.0))
    return round(wins / 82, 3)


def _lineup_team_stats(lineup: list) -> dict:
    return {
        "avg_offensive_rating": round(float(np.mean([p["offensive_rating"] for p in lineup])), 1),
        "avg_defensive_rating": round(float(np.mean([p["defensive_rating"] for p in lineup])), 1),
        "total_rebounds":       round(float(sum(p["rebounds"] for p in lineup)), 1),
        "total_assists":        round(float(sum(p["assists"] for p in lineup)), 1),
        "total_blocks":         round(float(sum(p["blocks"] for p in lineup)), 1),
        "total_steals":         round(float(sum(p["steals"] for p in lineup)), 1),
        "avg_ts_pct":           round(float(np.mean([p["ts_pct"] for p in lineup])), 3),
        "avg_three_pt_pct":     round(float(np.mean([p["three_pt_pct"] for p in lineup])), 3),
        "total_win_shares":     round(float(sum(p["win_shares"] for p in lineup)), 1),
        "avg_bpm":              round(float(np.mean([p["bpm"] for p in lineup])), 2),
        "predicted_win_pct":    _predict_win_pct(lineup),
        "predicted_wins_82":    round(_predict_win_pct(lineup) * 82),
    }


def generate_lineup(
    lineup_type: str,
    era: Optional[str] = None,
    season: Optional[str] = None,
    min_height: Optional[int] = None,
    max_height: Optional[int] = None,
    positions: Optional[list] = None,
) -> dict:

    if lineup_type not in LINEUP_WEIGHTS:
        return {"error": f"Unknown lineup type: {lineup_type}"}

    session = get_session()
    df = _query_players(session, era, season, min_height, max_height, positions)
    session.close()

    if df.empty:
        return {"error": "No players found matching filters. Run the data pipeline first."}

    # Minimum 30 games played for all lineup types
    df = df[df["games_played"] >= 30].copy()
    if df.empty:
        return {"error": "No players found who played at least 30 games matching these filters."}

    # Per-filter caveats to eliminate small-sample outliers:
    #
    # best_shooting:  min 30 three-point attempts (eliminates Dwight 1-for-1 type)
    #                 min 50 FG attempts (eliminates players who barely played offense)
    #
    # best_offense:   min 10 MPG (eliminates garbage-time ORTG inflation)
    #                 min 15 usage rate (eliminates spot-up players riding star teammates)
    #                 min 10 PPG (eliminates non-scorers with inflated ORTG)
    #
    # best_defense:   min 10 MPG (eliminates garbage-time DRTG)
    #                 min 1.0 combined blocks+steals (eliminates passive defenders)
    #
    # most_balanced:  min 15 usage rate (PER inflates for low-usage efficient players)
    #                 min 10 MPG
    #
    # small_ball:     min 30 three-point attempts (spacing requires real shooting volume)
    #                 min 10 MPG
    #
    # traditional:    min 15 MPG (rebounding inflates in short bursts)
    #                 min 5 rebounds/game (must actually rebound)

    if lineup_type == "best_shooting":
        df = df[
            (df["three_pt_attempts"] >= 100) &   # min ~1.5 attempts/game over 65 games
            (df["fg_attempts"] >= 200) &           # meaningful offensive role
            (df["minutes_per_game"] >= 20)         # starter/rotation player
        ].copy()

    elif lineup_type == "best_offense":
        df = df[
            (df["minutes_per_game"] >= 20) &
            (df["usage_rate"] >= 18) &
            (df["points"] >= 12)
        ].copy()

    elif lineup_type == "best_defense":
        df = df[
            (df["minutes_per_game"] >= 20) &
            ((df["blocks"] + df["steals"]) >= 1.0)
        ].copy()

    elif lineup_type == "most_balanced":
        df = df[
            (df["minutes_per_game"] >= 20) &
            (df["usage_rate"] >= 18)
        ].copy()

    elif lineup_type == "small_ball":
        df = df[
            (df["three_pt_attempts"] >= 100) &    # must be a real shooter
            (df["minutes_per_game"] >= 20)
        ].copy()

    elif lineup_type == "traditional":
        df = df[
            (df["minutes_per_game"] >= 20) &
            (df["rebounds"] >= 5)
        ].copy()

    if df.empty:
        return {"error": f"No qualified players found for '{lineup_type}' with the given filters. Try broadening your search."}

    weights  = LINEUP_WEIGHTS[lineup_type]
    slots    = LINEUP_SLOTS[lineup_type]

    # Compute max AND min for every stat used in weights
    # Min is needed for correct normalization of negative-weight stats (lower=better)
    maxvals = {}
    for col in weights:
        if col in df.columns:
            maxvals[col]          = float(df[col].max())
            maxvals[f"{col}_min"] = float(df[col].min())

    # Pre-score every player
    df["_score"] = df.apply(lambda r: _score(r.to_dict(), weights, maxvals), axis=1)

    # Build lineup slot by slot
    from collections import Counter
    slot_counts = Counter(slots)

    lineup      = []
    used_ids    = set()
    used_names  = set()
    snubs_by_pos = {}

    for pos, count in slot_counts.items():
        # Get ALL players at this position sorted by score — no cap
        candidates = _get_top_for_pos(df, pos, weights, maxvals, used_ids)

        picked = 0
        for candidate in candidates:
            if candidate["name"] not in used_names and candidate["id"] not in used_ids:
                candidate["_score"] = _score(candidate, weights, maxvals)
                # Assign the slot position so the card shows the right label
                candidate = dict(candidate)
                candidate["position"] = pos
                lineup.append(candidate)
                used_ids.add(candidate["id"])
                used_names.add(candidate["name"])

                # Find snubs for this position
                if picked == 0:
                    snubs_by_pos[pos] = _notable_snubs(
                        df, pos, candidate, weights, maxvals, lineup_type
                    )

                picked += 1
                if picked == count:
                    break

        # Fallback: fill from any remaining player
        if picked < count:
            remaining = df[~df["id"].isin(used_ids)].sort_values("_score", ascending=False)
            for _, row in remaining.iterrows():
                if row["name"] not in used_names:
                    r = row.to_dict()
                    r["position"] = pos
                    lineup.append(r)
                    used_ids.add(r["id"])
                    used_names.add(r["name"])
                    picked += 1
                    if picked == count:
                        break

    if len(lineup) < 5:
        return {"error": "Could not build a full lineup with the given filters."}

    # Format players
    players_out = []
    for p in lineup:
        players_out.append({
            "name":             str(p["name"]),
            "position":         str(p["position"]),
            "season":           str(p["season"]),
            "team":             str(p["team"]),
            "points":           round(float(p.get("points", 0)), 1),
            "rebounds":         round(float(p.get("rebounds", 0)), 1),
            "assists":          round(float(p.get("assists", 0)), 1),
            "blocks":           round(float(p.get("blocks", 0)), 1),
            "steals":           round(float(p.get("steals", 0)), 1),
            "fg_pct":           round(float(p.get("fg_pct", 0)), 3),
            "three_pt_pct":     round(float(p.get("three_pt_pct", 0)), 3),
            "ts_pct":           round(float(p.get("ts_pct", 0)), 3),
            "offensive_rating": round(float(p.get("offensive_rating", 0)), 1),
            "defensive_rating": round(float(p.get("defensive_rating", 0)), 1),
            "net_rating":       round(float(p.get("net_rating", 0)), 1),
            "bpm":              round(float(p.get("bpm", 0)), 2),
            "win_shares":       round(float(p.get("win_shares", 0)), 1),
            "per":              round(float(p.get("per", 0)), 1),
            "is_ball_handler":           bool(p.get("is_ball_handler", False)),
            "is_rim_protector":          bool(p.get("is_rim_protector", False)),
            "is_three_point_specialist": bool(p.get("is_three_point_specialist", False)),
        })

    summary = _build_lineup_summary(
        players_out, lineup_type, snubs_by_pos, df, weights, maxvals
    )

    return {
        "lineup_type":   lineup_type,
        "players":       players_out,
        "team_stats":    _lineup_team_stats(players_out),
        "synergy_score": round(float(sum(p.get("_score", 0) for p in lineup)), 4),
        "summary":       summary,
    }
