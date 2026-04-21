import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "data")

DATABASE_URL = f"sqlite:///{os.path.join(DATA_DIR, 'nba.db')}"

SCRAPE_DELAY = 3  # seconds between requests to avoid rate limiting

POSITION_MAP = {
    "PG": "Point Guard",
    "SG": "Shooting Guard",
    "SF": "Small Forward",
    "PF": "Power Forward",
    "C":  "Center"
}

# Minimum lineup constraints
LINEUP_CONSTRAINTS = {
    "min_rebounds": 35.0,
    "min_blocks": 2.0,
    "max_offensive_rating": 120.0,
    "min_defensive_rating_threshold": 105.0,
    "must_have_ball_handler": True,
    "must_have_rim_protector": True,
}

LINEUP_TYPES = [
    "best_shooting",
    "best_offense",
    "best_defense",
    "most_balanced",
    "small_ball",
    "traditional",
]
