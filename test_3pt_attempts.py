import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import time
from nba_api.stats.endpoints import leaguedashplayerstats

time.sleep(1)
r = leaguedashplayerstats.LeagueDashPlayerStats(
    season="2023-24", per_mode_detailed="Totals",
    measure_type_detailed_defense="Base",
    season_type_all_star="Regular Season", timeout=60
)
df = r.get_data_frames()[0]
print("Available columns:", [c for c in df.columns if any(x in c for x in ["3", "FG", "FT", "MIN", "GP"])])
print()
print("Low 3PT attempt players with high pct:")
low_att = df[df["FG3A"] < 30].sort_values("FG3_PCT", ascending=False).head(10)
print(low_att[["PLAYER_NAME","GP","MIN","FG3A","FG3M","FG3_PCT"]].to_string())
print()
print("High 3PT attempt players:")
high_att = df[df["FG3A"] >= 200].sort_values("FG3_PCT", ascending=False).head(10)
print(high_att[["PLAYER_NAME","GP","MIN","FG3A","FG3M","FG3_PCT"]].to_string())
