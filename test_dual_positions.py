import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import time
from nba_api.stats.endpoints import leaguedashplayerstats

def fetch_pos(pos_group):
    time.sleep(1.5)
    return leaguedashplayerstats.LeagueDashPlayerStats(
        season="2023-24", per_mode_detailed="PerGame",
        measure_type_detailed_defense="Base",
        player_position_abbreviation_nullable=pos_group,
        season_type_all_star="Regular Season", timeout=60
    ).get_data_frames()[0]

print("Fetching G, F, C groups...")
g = fetch_pos("G")
f = fetch_pos("F")
c = fetch_pos("C")

g_names = set(g["PLAYER_NAME"])
f_names = set(f["PLAYER_NAME"])
c_names = set(c["PLAYER_NAME"])

gf = g_names & f_names
fc = f_names & c_names

print(f"\nG only: {len(g_names - f_names - c_names)}")
print(f"F only: {len(f_names - g_names - c_names)}")
print(f"C only: {len(c_names - g_names - f_names)}")
print(f"G+F dual: {len(gf)}")
print(f"F+C dual: {len(fc)}")

print("\nDual G+F players with GP per group:")
for name in sorted(gf)[:8]:
    gp_g = int(g[g["PLAYER_NAME"]==name]["GP"].values[0])
    gp_f = int(f[f["PLAYER_NAME"]==name]["GP"].values[0])
    print(f"  {name:<28} G-GP={gp_g:>3}  F-GP={gp_f:>3}  primary={'G' if gp_g >= gp_f else 'F'}")

print("\nDual F+C players with GP per group:")
for name in sorted(fc)[:8]:
    gp_f = int(f[f["PLAYER_NAME"]==name]["GP"].values[0])
    gp_c = int(c[c["PLAYER_NAME"]==name]["GP"].values[0])
    print(f"  {name:<28} F-GP={gp_f:>3}  C-GP={gp_c:>3}  primary={'F' if gp_f >= gp_c else 'C'}")
