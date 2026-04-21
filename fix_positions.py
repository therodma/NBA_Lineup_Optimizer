"""
Fix player positions in the existing database using stat-based heuristics.
No scraping needed — works on the data already in nba.db.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.models.database import get_session, Player

# Known star players and their correct positions
KNOWN_POSITIONS = {
    "Stephen Curry":          "PG",
    "LeBron James":           "SF",
    "Kevin Durant":           "SF",
    "Nikola Jokic":           "C",
    "Nikola Joki":            "C",  # unicode fallback
    "Jusuf Nurkic":           "C",
    "Jusuf Nurki":            "C",  # unicode fallback
    "Bojan Bogdanovic":       "SF",
    "Bogdan Bogdanovic":      "SG",
    "Giannis Antetokounmpo":  "PF",
    "Joel Embiid":            "C",
    "Jayson Tatum":           "SF",
    "James Harden":           "PG",
    "Damian Lillard":         "PG",
    "Luka Doncic":            "PG",
    "Devin Booker":           "SG",
    "Donovan Mitchell":       "SG",
    "Trae Young":             "PG",
    "Ja Morant":              "PG",
    "Zion Williamson":        "PF",
    "Anthony Davis":          "C",
    "Bam Adebayo":            "C",
    "Rudy Gobert":            "C",
    "Draymond Green":         "PF",
    "Kawhi Leonard":          "SF",
    "Paul George":            "SF",
    "Jimmy Butler":           "SF",
    "Khris Middleton":        "SF",
    "Bradley Beal":           "SG",
    "Klay Thompson":          "SG",
    "Chris Paul":             "PG",
    "Russell Westbrook":      "PG",
    "Kyrie Irving":           "PG",
    "Kemba Walker":           "PG",
    "De'Aaron Fox":           "PG",
    "Fred VanVleet":          "PG",
    "Jrue Holiday":           "PG",
    "Mike Conley":            "PG",
    "Kyle Lowry":             "PG",
    "Tyrese Haliburton":      "PG",
    "Shai Gilgeous-Alexander":"SG",
    "Anthony Edwards":        "SG",
    "Zach LaVine":            "SG",
    "CJ McCollum":            "SG",
    "Buddy Hield":            "SG",
    "Duncan Robinson":        "SG",
    "Seth Curry":             "SG",
    "Joe Harris":             "SG",
    "Desmond Bane":           "SG",
    "Jordan Poole":           "SG",
    "Andrew Wiggins":         "SF",
    "OG Anunoby":             "SF",
    "Mikal Bridges":          "SF",
    "Harrison Barnes":        "SF",
    "Tobias Harris":          "PF",
    "Pascal Siakam":          "PF",
    "Julius Randle":          "PF",
    "John Collins":           "PF",
    "Jaren Jackson Jr.":      "PF",
    "Evan Mobley":            "C",
    "Jarrett Allen":          "C",
    "Clint Capela":           "C",
    "Brook Lopez":            "C",
    "Karl-Anthony Towns":     "C",
    "Deandre Ayton":          "C",
    "Mitchell Robinson":      "C",
    "Ivica Zubac":            "C",
    "Jonas Valanciunas":      "C",
    "Andre Drummond":         "C",
    "Bobby Portis":           "PF",
    "Domantas Sabonis":       "C",
    "Chet Holmgren":          "C",
    "Victor Wembanyama":      "C",
    "Paolo Banchero":         "PF",
    "Franz Wagner":           "SF",
    "Scottie Barnes":         "PF",
    "Jalen Green":            "SG",
    "Alperen Sengun":         "C",
}


def _stat_based_position(p: Player) -> str:
    """Assign position from stats when no known mapping exists."""
    ast = p.assists or 0
    blk = p.blocks or 0
    reb = p.rebounds or 0
    pts = p.points or 0
    ht  = p.height_inches or 0

    # Centers: tall + rebounds/blocks
    if ht >= 82 or (blk >= 1.5 and reb >= 8):
        return "C"
    if blk >= 1.2 and reb >= 7:
        return "PF"
    # Guards: high assists
    if ast >= 6.0:
        return "PG"
    if ast >= 3.5 and pts >= 12:
        return "SG"
    # Forwards
    if reb >= 6 and blk >= 0.8:
        return "PF"
    if pts >= 15 and ast < 3:
        return "SF"
    if ast >= 2.5:
        return "SG"
    return "SF"


def fix_positions():
    session = get_session()
    players = session.query(Player).all()

    fixed_known = 0
    fixed_stat  = 0

    for p in players:
        # First check known mapping (exact and partial for unicode names)
        matched = False
        for known_name, known_pos in KNOWN_POSITIONS.items():
            if p.name == known_name or p.name.lower().startswith(known_name.split()[0].lower()):
                if p.name.split()[-1].lower()[:4] == known_name.split()[-1].lower()[:4]:
                    if p.position != known_pos:
                        p.position = known_pos
                        fixed_known += 1
                    matched = True
                    break
        if not matched:
            new_pos = _stat_based_position(p)
            if p.position != new_pos:
                p.position = new_pos
                fixed_stat += 1

    session.commit()

    # Print position breakdown
    print(f"Fixed {fixed_known} known players, {fixed_stat} stat-based players")
    print("\nPosition breakdown after fix:")
    for pos in ["PG", "SG", "SF", "PF", "C"]:
        count = session.query(Player).filter(Player.position == pos).count()
        print(f"  {pos}: {count}")

    # Verify key players
    print("\nKey player positions:")
    for name in ["Stephen Curry", "LeBron James", "Nikola Jokic", "Giannis Antetokounmpo",
                 "Joel Embiid", "Jayson Tatum", "Kevin Durant", "James Harden"]:
        p = session.query(Player).filter(Player.name == name).order_by(Player.season.desc()).first()
        if p:
            print(f"  {p.name}: {p.position} ({p.season}) | pts={p.points:.1f} | 3pt={p.three_pt_pct:.3f}")
        else:
            print(f"  {name}: NOT FOUND IN DB")

    session.close()


if __name__ == "__main__":
    fix_positions()
