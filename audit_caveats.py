import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backend.models.database import get_session, Player

s = get_session()

print("=" * 90)
print("SHOOTING OUTLIERS — high 3PT% but low volume (< 30 attempts proxy)")
print("3PT attempts not stored, using: 3pt_pct >= 0.45 AND points < 12 as proxy for low volume")
print("=" * 90)
players = s.query(Player).filter(
    Player.three_pt_pct >= 0.45,
    Player.points < 12,
    Player.games_played >= 30,
    Player.season == "2023-24"
).order_by(Player.three_pt_pct.desc()).limit(15).all()
for p in players:
    n = p.name.encode("ascii","replace").decode()
    print(f"  {n:<28} {p.position} 3pt={p.three_pt_pct*100:.1f}% pts={p.points:.1f} gp={p.games_played}")

print()
print("=" * 90)
print("DEFENSE OUTLIERS — great DRTG but low usage/minutes (garbage time defenders)")
print("=" * 90)
players = s.query(Player).filter(
    Player.defensive_rating <= 100,
    Player.points < 8,
    Player.games_played >= 30,
    Player.season == "2023-24"
).order_by(Player.defensive_rating).limit(15).all()
for p in players:
    n = p.name.encode("ascii","replace").decode()
    print(f"  {n:<28} {p.position} drtg={p.defensive_rating:.1f} pts={p.points:.1f} blk={p.blocks:.1f} stl={p.steals:.1f} gp={p.games_played}")

print()
print("=" * 90)
print("OFFENSE OUTLIERS — great ORTG but low usage (benefiting from playing with stars)")
print("=" * 90)
players = s.query(Player).filter(
    Player.offensive_rating >= 120,
    Player.points < 10,
    Player.games_played >= 30,
    Player.season == "2023-24"
).order_by(Player.offensive_rating.desc()).limit(15).all()
for p in players:
    n = p.name.encode("ascii","replace").decode()
    print(f"  {n:<28} {p.position} ortg={p.offensive_rating:.1f} pts={p.points:.1f} usg={p.usage_rate:.1f} gp={p.games_played}")

print()
print("=" * 90)
print("BALANCED OUTLIERS — high PER but low minutes/usage (inflated by small role)")
print("=" * 90)
players = s.query(Player).filter(
    Player.per >= 25,
    Player.usage_rate < 15,
    Player.games_played >= 30,
    Player.season == "2023-24"
).order_by(Player.per.desc()).limit(15).all()
for p in players:
    n = p.name.encode("ascii","replace").decode()
    print(f"  {n:<28} {p.position} per={p.per:.1f} usg={p.usage_rate:.1f} pts={p.points:.1f} gp={p.games_played}")

print()
print("=" * 90)
print("TRADITIONAL OUTLIERS — high rebounds but low minutes (garbage time bigs)")
print("=" * 90)
players = s.query(Player).filter(
    Player.rebounds >= 12,
    Player.points < 8,
    Player.games_played >= 30,
    Player.season == "2023-24"
).order_by(Player.rebounds.desc()).limit(15).all()
for p in players:
    n = p.name.encode("ascii","replace").decode()
    print(f"  {n:<28} {p.position} reb={p.rebounds:.1f} pts={p.points:.1f} blk={p.blocks:.1f} gp={p.games_played} mpg={p.minutes_per_game:.1f}")

print()
print("=" * 90)
print("FG% OUTLIERS — high FG% but low scoring (dunkers/lob catchers only)")
print("=" * 90)
players = s.query(Player).filter(
    Player.fg_pct >= 0.65,
    Player.points < 12,
    Player.games_played >= 30,
    Player.season == "2023-24"
).order_by(Player.fg_pct.desc()).limit(15).all()
for p in players:
    n = p.name.encode("ascii","replace").decode()
    print(f"  {n:<28} {p.position} fg={p.fg_pct*100:.1f}% pts={p.points:.1f} gp={p.games_played} mpg={p.minutes_per_game:.1f}")

s.close()
