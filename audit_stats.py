import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backend.models.database import get_session, Player

s = get_session()

print("=" * 100)
print("TOP 20 SCORERS 2023-24 — checking stat accuracy")
print("=" * 100)
players = s.query(Player).filter(Player.season == "2023-24").order_by(Player.points.desc()).limit(20).all()
print(f"{'Name':<28} {'Pos':<4} {'PTS':>5} {'3PT%':>6} {'FG%':>5} {'TS%':>5} {'ORTG':>6} {'DRTG':>6} {'NET':>5} {'PER':>5} {'WS':>5} {'HT':>4}")
print("-" * 100)
for p in players:
    name = p.name.encode("ascii", "replace").decode()
    print(f"{name:<28} {p.position:<4} {p.points:>5.1f} {p.three_pt_pct*100:>5.1f}% {p.fg_pct*100:>4.1f}% {p.ts_pct*100:>4.1f}% {p.offensive_rating:>6.1f} {p.defensive_rating:>6.1f} {p.net_rating:>5.1f} {p.per:>5.1f} {p.win_shares:>5.1f} {p.height_inches:>4}")

print()
print("=" * 100)
print("REAL NBA 2023-24 STATS (per 36) for comparison:")
print("Embiid: 37.2pts, 11.7reb, 5.6ast, 34.7% 3pt, 61.6% TS, ORTG~119, DRTG~110")
print("Jokic:  26.4pts, 12.4reb, 9.0ast, 35.9% 3pt, 64.0% TS, ORTG~123, DRTG~112")
print("Curry:  29.1pts, 4.5reb, 6.3ast, 40.8% 3pt, 63.5% TS, ORTG~120, DRTG~113")
print("Tatum:  26.9pts, 8.1reb, 4.9ast, 37.6% 3pt, 59.1% TS, ORTG~121, DRTG~110")
print()

print("=" * 100)
print("CHECKING SPECIFIC PLAYERS")
print("=" * 100)
checks = ["Stephen Curry", "Joel Embiid", "Jayson Tatum", "LeBron James",
          "Kevin Durant", "Giannis Antetokounmpo", "James Harden", "Damian Lillard",
          "Luka Don", "Shai Gilgeous"]
for name_part in checks:
    players = s.query(Player).filter(
        Player.name.ilike(f"%{name_part.split()[0]}%"),
        Player.season == "2023-24"
    ).all()
    for p in players:
        n = p.name.encode("ascii", "replace").decode()
        print(f"{n:<28} {p.position:<4} pts={p.points:.1f} 3pt={p.three_pt_pct*100:.1f}% fg={p.fg_pct*100:.1f}% ts={p.ts_pct*100:.1f}% ortg={p.offensive_rating:.1f} drtg={p.defensive_rating:.1f} net={p.net_rating:.1f} per={p.per:.1f} ws={p.win_shares:.1f} ht={p.height_inches}")

print()
print("=" * 100)
print("POSITION DISTRIBUTION")
print("=" * 100)
for pos in ["PG", "SG", "SF", "PF", "C"]:
    count = s.query(Player).filter(Player.position == pos).count()
    print(f"  {pos}: {count}")

print()
print("=" * 100)
print("CHECKING ZERO/NULL STATS (data quality issues)")
print("=" * 100)
zero_ortg = s.query(Player).filter(Player.offensive_rating <= 1.0).count()
zero_3pt  = s.query(Player).filter(Player.three_pt_pct == 0).count()
zero_ts   = s.query(Player).filter(Player.ts_pct == 0).count()
zero_per  = s.query(Player).filter(Player.per == 0).count()
zero_ht   = s.query(Player).filter(Player.height_inches == 0).count()
total     = s.query(Player).count()
print(f"  Total players: {total}")
print(f"  Zero/bad offensive_rating: {zero_ortg} ({zero_ortg/total*100:.1f}%)")
print(f"  Zero three_pt_pct:         {zero_3pt} ({zero_3pt/total*100:.1f}%)")
print(f"  Zero ts_pct:               {zero_ts} ({zero_ts/total*100:.1f}%)")
print(f"  Zero per:                  {zero_per} ({zero_per/total*100:.1f}%)")
print(f"  Zero height:               {zero_ht} ({zero_ht/total*100:.1f}%)")

s.close()
