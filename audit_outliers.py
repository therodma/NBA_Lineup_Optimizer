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
    "best_shooting":  lambda d: d[(d["three_pt_attempts"] >= 30) & (d["fg_attempts"] >= 50) & (d["minutes_per_game"] >= 10)],
    "traditional":    lambda d: d[(d["minutes_per_game"] >= 15) & (d["rebounds"] >= 5)],
    "small_ball":     lambda d: d[(d["three_pt_attempts"] >= 30) & (d["minutes_per_game"] >= 15)],
}

# ── DANTE EXUM in best_shooting ──────────────────────────────────────────────
print("=" * 80)
print("WHY IS DANTE EXUM IN BEST SHOOTING?")
print("=" * 80)
filtered = CAVEATS["best_shooting"](df).copy()
weights  = LINEUP_WEIGHTS["best_shooting"]
maxvals  = {}
for col in weights:
    if col in filtered.columns:
        maxvals[col]          = float(filtered[col].max())
        maxvals[f"{col}_min"] = float(filtered[col].min())

filtered["_score"] = filtered.apply(lambda r: _score(r.to_dict(), weights, maxvals), axis=1)

# Show Dante Exum's full profile
exum = filtered[filtered["name"].str.contains("Exum", na=False)]
print("\nDante Exum stats:")
for _, r in exum.iterrows():
    print(f"  Season: {r['season']} | GP={r['games_played']} | MPG={r['minutes_per_game']:.1f}")
    print(f"  3PT%={r['three_pt_pct']*100:.1f}% on {r['three_pt_attempts']} attempts")
    print(f"  TS%={r['ts_pct']*100:.1f}% | FG%={r['fg_pct']*100:.1f}%")
    print(f"  ORTG={r['offensive_rating']:.1f} | BPM={r['bpm']:.2f} | WS={r['win_shares']:.1f} | NET={r['net_rating']:.1f}")
    print(f"  Score={r['_score']:.4f}")

print("\nTop 10 SGs in best_shooting (to see who Exum beat):")
sg = filtered[filtered["position"] == "SG"].nlargest(10, "_score")
for _, r in sg.iterrows():
    n = r["name"].encode("ascii","replace").decode()
    print(f"  {n:<28} score={r['_score']:.4f} | 3pt={r['three_pt_pct']*100:.1f}% ({r['three_pt_attempts']}att) | ts={r['ts_pct']*100:.1f}% | ortg={r['offensive_rating']:.1f} | bpm={r['bpm']:.2f} | mpg={r['minutes_per_game']:.1f} | gp={r['games_played']}")

# ── JONATHAN ISAAC in traditional SF ────────────────────────────────────────
print()
print("=" * 80)
print("WHY IS JONATHAN ISAAC IN TRADITIONAL SF?")
print("=" * 80)
filtered2 = CAVEATS["traditional"](df).copy()
weights2  = LINEUP_WEIGHTS["traditional"]
maxvals2  = {}
for col in weights2:
    if col in filtered2.columns:
        maxvals2[col]          = float(filtered2[col].max())
        maxvals2[f"{col}_min"] = float(filtered2[col].min())

filtered2["_score"] = filtered2.apply(lambda r: _score(r.to_dict(), weights2, maxvals2), axis=1)

isaac = filtered2[filtered2["name"].str.contains("Isaac", na=False)]
print("\nJonathan Isaac stats:")
for _, r in isaac.iterrows():
    print(f"  Season: {r['season']} | GP={r['games_played']} | MPG={r['minutes_per_game']:.1f}")
    print(f"  REB={r['rebounds']:.1f} | BLK={r['blocks']:.1f} | DRTG={r['defensive_rating']:.1f}")
    print(f"  WS={r['win_shares']:.1f} | PER={r['per']:.1f} | BPM={r['bpm']:.2f} | NET={r['net_rating']:.1f}")
    print(f"  Score={r['_score']:.4f}")

print("\nTop 10 SFs in traditional:")
sf = filtered2[filtered2["position"] == "SF"].nlargest(10, "_score")
for _, r in sf.iterrows():
    n = r["name"].encode("ascii","replace").decode()
    print(f"  {n:<28} score={r['_score']:.4f} | reb={r['rebounds']:.1f} | blk={r['blocks']:.1f} | drtg={r['defensive_rating']:.1f} | ws={r['win_shares']:.1f} | per={r['per']:.1f} | bpm={r['bpm']:.2f} | mpg={r['minutes_per_game']:.1f} | gp={r['games_played']}")

# ── DANNY GREEN as PF in small_ball ─────────────────────────────────────────
print()
print("=" * 80)
print("WHY IS DANNY GREEN APPEARING AS PF IN SMALL_BALL?")
print("=" * 80)
filtered3 = CAVEATS["small_ball"](df).copy()
weights3  = LINEUP_WEIGHTS["small_ball"]
maxvals3  = {}
for col in weights3:
    if col in filtered3.columns:
        maxvals3[col]          = float(filtered3[col].max())
        maxvals3[f"{col}_min"] = float(filtered3[col].min())

filtered3["_score"] = filtered3.apply(lambda r: _score(r.to_dict(), weights3, maxvals3), axis=1)

danny = filtered3[filtered3["name"].str.contains("Danny Green", na=False)]
print("\nDanny Green stats:")
for _, r in danny.iterrows():
    print(f"  Season: {r['season']} | pos={r['position']} | sec_pos={r['secondary_position']} | GP={r['games_played']} | MPG={r['minutes_per_game']:.1f}")
    print(f"  3PT%={r['three_pt_pct']*100:.1f}% ({r['three_pt_attempts']}att) | ORTG={r['offensive_rating']:.1f} | AST={r['assists']:.1f} | STL={r['steals']:.1f}")
    print(f"  BPM={r['bpm']:.2f} | WS={r['win_shares']:.1f} | NET={r['net_rating']:.1f} | Score={r['_score']:.4f}")

print("\nTop 10 PFs in small_ball:")
pf = filtered3[filtered3["position"] == "PF"].nlargest(10, "_score")
for _, r in pf.iterrows():
    n = r["name"].encode("ascii","replace").decode()
    print(f"  {n:<28} score={r['_score']:.4f} | pos={r['position']} | sec={r['secondary_position']} | 3pt={r['three_pt_pct']*100:.1f}% ({r['three_pt_attempts']}att) | ortg={r['offensive_rating']:.1f} | bpm={r['bpm']:.2f} | mpg={r['minutes_per_game']:.1f}")

print("\nTop 10 SFs in small_ball (second SF slot):")
sf2 = filtered3[filtered3["position"] == "SF"].nlargest(10, "_score")
for _, r in sf2.iterrows():
    n = r["name"].encode("ascii","replace").decode()
    print(f"  {n:<28} score={r['_score']:.4f} | 3pt={r['three_pt_pct']*100:.1f}% ({r['three_pt_attempts']}att) | ortg={r['offensive_rating']:.1f} | bpm={r['bpm']:.2f} | mpg={r['minutes_per_game']:.1f}")
