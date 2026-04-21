import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backend.models.database import get_session, Player

s = get_session()

print("Current position column samples (2023-24):")
players = s.query(Player).filter(Player.season == "2023-24").limit(30).all()
for p in players:
    n = p.name.encode("ascii", "replace").decode()
    print(f"  {n:<28} position='{p.position}'")

print("\nDo we have any secondary position data?")
# Check if any position has a slash or dash indicating dual position
dual = s.query(Player).filter(Player.position.like("%/%")).count()
dual2 = s.query(Player).filter(Player.position.like("%-%")).count()
print(f"  Positions with '/': {dual}")
print(f"  Positions with '-': {dual2}")

print("\nAll unique position values in DB:")
from sqlalchemy import distinct
positions = s.query(Player.position).distinct().all()
for p in positions:
    count = s.query(Player).filter(Player.position == p[0]).count()
    print(f"  '{p[0]}': {count} players")

s.close()
