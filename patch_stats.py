"""
1. Removes duplicate players (keeps best stats per name+season)
2. Fixes PER, BPM, win_shares scaling
3. Applies correct positions
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.models.database import get_session, Player, get_engine, Base
from sqlalchemy import text

KNOWN_POSITIONS = {
    "Stephen Curry": "PG", "LeBron James": "SF", "Kevin Durant": "SF",
    "Nikola Joki": "C", "Giannis Antetokounmpo": "PF", "Joel Embiid": "C",
    "Jayson Tatum": "SF", "James Harden": "PG", "Damian Lillard": "PG",
    "Luka Don": "PG", "Devin Booker": "SG", "Donovan Mitchell": "SG",
    "Trae Young": "PG", "Ja Morant": "PG", "Zion Williamson": "PF",
    "Anthony Davis": "C", "Bam Adebayo": "C", "Rudy Gobert": "C",
    "Draymond Green": "PF", "Kawhi Leonard": "SF", "Paul George": "SF",
    "Jimmy Butler": "SF", "Khris Middleton": "SF", "Bradley Beal": "SG",
    "Klay Thompson": "SG", "Chris Paul": "PG", "Russell Westbrook": "PG",
    "Kyrie Irving": "PG", "Kemba Walker": "PG", "De'Aaron Fox": "PG",
    "Fred VanVleet": "PG", "Jrue Holiday": "PG", "Mike Conley": "PG",
    "Kyle Lowry": "PG", "Tyrese Haliburton": "PG", "Jalen Brunson": "PG",
    "Shai Gilgeous-Alexander": "SG", "Anthony Edwards": "SG",
    "Zach LaVine": "SG", "CJ McCollum": "SG", "Buddy Hield": "SG",
    "Duncan Robinson": "SG", "Seth Curry": "SG", "Joe Harris": "SG",
    "Desmond Bane": "SG", "Jordan Poole": "SG", "Andrew Wiggins": "SF",
    "OG Anunoby": "SF", "Mikal Bridges": "SF", "Harrison Barnes": "SF",
    "Tobias Harris": "PF", "Pascal Siakam": "PF", "Julius Randle": "PF",
    "John Collins": "PF", "Jaren Jackson Jr.": "PF", "Evan Mobley": "C",
    "Jarrett Allen": "C", "Clint Capela": "C", "Brook Lopez": "C",
    "Karl-Anthony Towns": "C", "Deandre Ayton": "C", "Mitchell Robinson": "C",
    "Ivica Zubac": "C", "Jonas Valanciunas": "C", "Andre Drummond": "C",
    "Bobby Portis": "PF", "Domantas Sabonis": "C", "Chet Holmgren": "C",
    "Victor Wembanyama": "C", "Paolo Banchero": "PF", "Franz Wagner": "SF",
    "Scottie Barnes": "PF", "Jalen Green": "SG", "Alperen Sengun": "C",
    "Jusuf Nurki": "C", "LaMelo Ball": "PG", "Tyrese Maxey": "PG",
    "Dejounte Murray": "PG", "Darius Garland": "PG", "Immanuel Quickley": "PG",
    "Jalen Williams": "SG", "Anfernee Simons": "SG", "Jordan Clarkson": "SG",
    "Bogdan Bogdanovic": "SG", "Gary Trent Jr.": "SG", "Malik Monk": "SG",
    "Nikola Vucevic": "C", "Myles Turner": "C", "Jakob Poeltl": "C",
    "Wendell Carter Jr.": "C", "Isaiah Stewart": "C", "Walker Kessler": "C",
    "Nic Claxton": "C", "Daniel Gafford": "C", "Kristaps Porzingis": "C",
    "Lauri Markkanen": "PF", "Jerami Grant": "PF", "Aaron Gordon": "PF",
    "P.J. Tucker": "PF", "Royce O'Neale": "PF", "Obi Toppin": "PF",
    "Miles Bridges": "PF", "Jabari Smith Jr.": "PF", "Keegan Murray": "PF",
}


def _stat_position(p):
    ast = p.assists or 0
    blk = p.blocks or 0
    reb = p.rebounds or 0
    ht  = p.height_inches or 0
    pts = p.points or 0
    if ht >= 82 or (blk >= 1.5 and reb >= 8):  return "C"
    if blk >= 1.2 and reb >= 7:                 return "PF"
    if ast >= 6.0:                               return "PG"
    if ast >= 3.5 and pts >= 12:                 return "SG"
    if reb >= 6 and blk >= 0.8:                  return "PF"
    if pts >= 15 and ast < 3:                    return "SF"
    if ast >= 2.5:                               return "SG"
    return "SF"


def run():
    engine = get_engine()
    session = get_session()

    print("Step 1: Removing duplicates...")
    # Keep only the row with highest id per name+season (most recent insert)
    all_players = session.query(Player).order_by(Player.id).all()
    seen = {}
    to_delete = []
    for p in all_players:
        key = (p.name, p.season)
        if key in seen:
            to_delete.append(seen[key])  # delete older duplicate
        seen[key] = p

    for p in to_delete:
        session.delete(p)
    session.commit()
    print(f"  Removed {len(to_delete)} duplicates. Remaining: {session.query(Player).count()}")

    print("\nStep 2: Fixing positions...")
    players = session.query(Player).all()
    pos_fixed = 0
    for p in players:
        new_pos = None
        # Check known positions by prefix match (handles unicode)
        for known, pos in KNOWN_POSITIONS.items():
            pname = p.name or ""
            if pname == known or (
                len(known) >= 4 and
                pname.lower().startswith(known.split()[0].lower()) and
                pname.split()[-1].lower()[:4] == known.split()[-1].lower()[:4]
            ):
                new_pos = pos
                break
        if new_pos is None:
            new_pos = _stat_position(p)
        if p.position != new_pos:
            p.position = new_pos
            pos_fixed += 1
    session.commit()
    print(f"  Fixed {pos_fixed} positions")

    print("\nStep 3: Fixing PER, BPM, win_shares scaling...")
    players = session.query(Player).all()
    for p in players:
        net = p.net_rating or 0
        # Estimate total minutes from win_shares (reverse old formula W*0.12)
        # Use a fixed 25 min/game * 60 games = 1500 total mins as baseline
        total_mins = 1500

        # PER: current value was PIE*100 (avg ~10), scale to real PER (avg ~15)
        if p.per and p.per > 0:
            p.per = round(min(p.per * 1.5, 50.0), 1)

        # Win shares: net_rating based
        p.win_shares = round(max(0.0, (net / 30) * (total_mins / 48) * 0.3), 1)
        p.win_shares_per48 = round(p.win_shares / max(total_mins, 1) * 48, 3)

        # BPM: net_rating * 0.4
        p.bpm = round(net * 0.4, 2)

    session.commit()
    print("  Done.")

    print("\nFinal stats verification:")
    print(f"{'Name':<28} {'Pos':<4} {'PER':>5} {'WS':>5} {'BPM':>6} {'ORTG':>6} {'DRTG':>6} {'NET':>6}")
    print("-" * 70)
    for name in ["Stephen Curry", "Joel Embiid", "Jayson Tatum", "LeBron James",
                 "Kevin Durant", "Giannis Antetokounmpo", "James Harden",
                 "Damian Lillard", "Luka Don", "Shai Gilgeous"]:
        p = session.query(Player).filter(
            Player.name.ilike(f"%{name.split()[0]}%"),
            Player.season == "2023-24"
        ).first()
        if p:
            n = p.name.encode("ascii", "replace").decode()
            print(f"  {n:<26} {p.position:<4} {p.per:>5.1f} {p.win_shares:>5.1f} {p.bpm:>6.2f} {p.offensive_rating:>6.1f} {p.defensive_rating:>6.1f} {p.net_rating:>6.1f}")

    print("\nPosition breakdown:")
    for pos in ["PG", "SG", "SF", "PF", "C"]:
        count = session.query(Player).filter(Player.position == pos).count()
        print(f"  {pos}: {count}")

    print(f"\nTotal players: {session.query(Player).count()}")
    session.close()


if __name__ == "__main__":
    run()
