import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.models.optimizer import generate_lineup
from backend.api.app import app

TYPES = ["most_balanced", "traditional", "best_shooting", "best_offense", "best_defense", "small_ball"]

print("=" * 60)
print("Testing optimizer directly")
print("=" * 60)
all_ok = True
for t in TYPES:
    r = generate_lineup(t, season="2023-24")
    if r.get("error"):
        print(f"FAIL  {t}: {r['error']}")
        all_ok = False
    else:
        positions = [p["position"] for p in r["players"]]
        names = [p["name"].encode("ascii", "replace").decode() for p in r["players"]]
        dups = len(names) != len(set(names))
        print(f"OK    {t}: {list(zip(names, positions))} {'DUPLICATES!' if dups else ''}")

print()
print("=" * 60)
print("Testing API routes")
print("=" * 60)
client = app.test_client()

r = client.get("/api/health")
print(f"GET  /api/health     -> {r.status_code} {r.get_json()}")

r = client.get("/api/filters")
print(f"GET  /api/filters    -> {r.status_code} keys={list(r.get_json().keys())}")

for t in TYPES:
    r = client.post("/api/lineup", json={"lineup_type": t, "season": "2023-24"})
    data = r.get_json()
    if data.get("error"):
        print(f"POST /api/lineup [{t}] -> {r.status_code} ERROR: {data['error']}")
        all_ok = False
    else:
        print(f"POST /api/lineup [{t}] -> {r.status_code} OK ({len(data['players'])} players)")

print()
print("ALL TESTS PASSED" if all_ok else "SOME TESTS FAILED")
