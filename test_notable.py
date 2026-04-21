import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backend.models.database import get_session, Player

s = get_session()
notable = ["Curry", "LeBron", "Durant", "Jokic", "Giannis", "Embiid", "Tatum", "Harden", "Lillard", "Mitchell"]
for name in notable:
    players = s.query(Player).filter(Player.name.ilike(f"%{name}%")).order_by(Player.season.desc()).all()
    for p in players[:1]:
        print(f"{p.name} | {p.position} | {p.season} | 3pt={p.three_pt_pct:.3f} | pts={p.points:.1f} | per={p.per:.1f} | ortg={p.offensive_rating:.1f} | net={p.net_rating:.1f}")

print("\nTotal players:", s.query(Player).count())
print("Positions:", {pos: s.query(Player).filter(Player.position==pos).count() for pos in ["PG","SG","SF","PF","C"]})
print("Seasons:", [r[0] for r in s.query(Player.season).distinct().order_by(Player.season).all()])
s.close()
