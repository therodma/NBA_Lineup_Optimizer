import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd
from backend.models.database import get_session, Player
from backend.models.optimizer import LINEUP_WEIGHTS, _score, _query_players

s = get_session()
df = _query_players(s, None, None, None, None, None)
s.close()

weights = LINEUP_WEIGHTS["best_shooting"]

# Apply caveats
df = df[df["games_played"] >= 30].copy()
df = df[(df["three_pt_attempts"] >= 30) & (df["fg_attempts"] >= 50)].copy()

maxvals = {col: float(df[col].max()) for col in weights if col in df.columns}
df["_score"] = df.apply(lambda r: _score(r.to_dict(), weights, maxvals), axis=1)

print("BEST SHOOTING WEIGHTS:", weights)
print()
print("Top 10 at each position (qualified players only):")
for pos in ["PG", "SG", "SF", "PF", "C"]:
    pos_df = df[df["position"] == pos].nlargest(10, "_score")
    print(f"\n--- {pos} ---")
    print(f"{'Name':<28} {'Score':>6} {'3PT%':>6} {'TS%':>6} {'FG%':>5} {'ORTG':>6} {'BPM':>6} {'PER':>5} {'WS':>5} {'3PA':>5} {'GP':>4}")
    for _, r in pos_df.iterrows():
        n = r["name"].encode("ascii","replace").decode()
        print(f"  {n:<26} {r['_score']:>6.4f} {r['three_pt_pct']*100:>5.1f}% {r['ts_pct']*100:>5.1f}% {r['fg_pct']*100:>4.1f}% {r['offensive_rating']:>6.1f} {r['bpm']:>6.2f} {r['per']:>5.1f} {r['win_shares']:>5.1f} {r['three_pt_attempts']:>5} {r['games_played']:>4}")

print()
print("Thomas Bryant specifically:")
tb = df[df["name"].str.contains("Bryant", na=False)]
for _, r in tb.iterrows():
    n = r["name"].encode("ascii","replace").decode()
    print(f"  {n} | pos={r['position']} | 3pt={r['three_pt_pct']*100:.1f}% | ts={r['ts_pct']*100:.1f}% | fg={r['fg_pct']*100:.1f}% | ortg={r['offensive_rating']:.1f} | bpm={r['bpm']:.2f} | score={r['_score']:.4f} | 3pa={r['three_pt_attempts']} | gp={r['games_played']}")
