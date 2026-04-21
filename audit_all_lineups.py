import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd
from backend.models.database import get_session, Player
from backend.models.optimizer import LINEUP_WEIGHTS, _score, _query_players

s = get_session()
df = _query_players(s, None, None, None, None, None)
s.close()

df = df[df["games_played"] >= 30].copy()

CAVEATS = {
    "best_shooting":  lambda d: d[(d["three_pt_attempts"] >= 30) & (d["fg_attempts"] >= 50)],
    "best_offense":   lambda d: d[(d["minutes_per_game"] >= 10) & (d["usage_rate"] >= 15) & (d["points"] >= 10)],
    "best_defense":   lambda d: d[(d["minutes_per_game"] >= 10) & ((d["blocks"] + d["steals"]) >= 1.0)],
    "most_balanced":  lambda d: d[(d["minutes_per_game"] >= 10) & (d["usage_rate"] >= 15)],
    "small_ball":     lambda d: d[(d["three_pt_attempts"] >= 30) & (d["minutes_per_game"] >= 10)],
    "traditional":    lambda d: d[(d["minutes_per_game"] >= 15) & (d["rebounds"] >= 5)],
}

for lineup_type, weights in LINEUP_WEIGHTS.items():
    filtered = CAVEATS[lineup_type](df).copy()
    maxvals = {col: float(filtered[col].max()) for col in weights if col in filtered.columns}
    filtered["_score"] = filtered.apply(lambda r: _score(r.to_dict(), weights, maxvals), axis=1)

    print("=" * 100)
    print(f"LINEUP: {lineup_type.upper()}  |  Weights: {weights}")
    print(f"Qualified pool: {len(filtered)} players")
    print("=" * 100)

    for pos in ["PG", "SG", "SF", "PF", "C"]:
        pos_df = filtered[filtered["position"] == pos].nlargest(5, "_score")
        sec_df = filtered[
            (filtered["secondary_position"] == pos) &
            (filtered["position"] != pos)
        ].nlargest(3, "_score")

        print(f"\n  {pos} — Primary candidates:")
        print(f"  {'Name':<26} {'Scr':>5} {'3PT%':>5} {'TS%':>5} {'FG%':>5} {'ORTG':>5} {'DRTG':>5} {'BPM':>5} {'WS':>4} {'NET':>5} {'REB':>4} {'AST':>4} {'BLK':>4} {'STL':>4} {'PER':>4} {'MPG':>5} {'GP':>3}")
        for _, r in pos_df.iterrows():
            n = r["name"].encode("ascii","replace").decode()[:24]
            print(f"  {n:<26} {r['_score']:>5.3f} {r['three_pt_pct']*100:>4.1f}% {r['ts_pct']*100:>4.1f}% {r['fg_pct']*100:>4.1f}% {r['offensive_rating']:>5.1f} {r['defensive_rating']:>5.1f} {r['bpm']:>5.2f} {r['win_shares']:>4.1f} {r['net_rating']:>5.1f} {r['rebounds']:>4.1f} {r['assists']:>4.1f} {r['blocks']:>4.1f} {r['steals']:>4.1f} {r['per']:>4.1f} {r['minutes_per_game']:>5.1f} {r['games_played']:>3}")

        if not sec_df.empty:
            print(f"  {pos} — Secondary candidates (primary pos shown in brackets):")
            for _, r in sec_df.iterrows():
                n = r["name"].encode("ascii","replace").decode()[:24]
                print(f"  [{r['position']}] {n:<24} {r['_score']:>5.3f} {r['three_pt_pct']*100:>4.1f}% {r['ts_pct']*100:>4.1f}% {r['bpm']:>5.2f} {r['net_rating']:>5.1f} {r['per']:>4.1f}")

    print()
