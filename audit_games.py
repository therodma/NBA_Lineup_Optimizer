import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backend.models.database import get_session, Player

s = get_session()

print("Players with 90%+ FG% in 2023-24 (small sample suspects):")
players = s.query(Player).filter(
    Player.fg_pct >= 0.90,
    Player.season == "2023-24"
).order_by(Player.fg_pct.desc()).all()
for p in players[:15]:
    n = p.name.encode("ascii","replace").decode()
    print(f"  {n:<28} {p.position} fg={p.fg_pct*100:.1f}% pts={p.points:.1f} ws={p.win_shares:.1f}")

print()
print("Players with 80%+ 3PT% in 2023-24:")
players = s.query(Player).filter(
    Player.three_pt_pct >= 0.80,
    Player.season == "2023-24"
).order_by(Player.three_pt_pct.desc()).all()
for p in players[:15]:
    n = p.name.encode("ascii","replace").decode()
    print(f"  {n:<28} {p.position} 3pt={p.three_pt_pct*100:.1f}% pts={p.points:.1f} ws={p.win_shares:.1f}")

print()
print("Win shares distribution 2023-24 (proxy for games played):")
all_p = s.query(Player).filter(Player.season == "2023-24").all()
buckets = {"ws=0": 0, "ws<1": 0, "ws<2": 0, "ws<3": 0, "ws>=3": 0}
for p in all_p:
    ws = p.win_shares or 0
    if ws == 0:       buckets["ws=0"] += 1
    elif ws < 1:      buckets["ws<1"] += 1
    elif ws < 2:      buckets["ws<2"] += 1
    elif ws < 3:      buckets["ws<3"] += 1
    else:             buckets["ws>=3"] += 1
for k, v in buckets.items():
    print(f"  {k}: {v} players")

print(f"\nTotal 2023-24 players: {len(all_p)}")
print("Note: NBA regular season is 82 games. Win shares >= 3 roughly = 40+ games played")
s.close()
