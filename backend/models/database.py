from sqlalchemy import create_engine, Column, Integer, Float, String, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.config import DATABASE_URL

Base = declarative_base()

class Player(Base):
    __tablename__ = "players"

    id              = Column(Integer, primary_key=True)
    name            = Column(String, nullable=False)
    position        = Column(String)          # PG, SG, SF, PF, C
    height_inches   = Column(Integer)
    era             = Column(String)          # e.g. "2010s", "2020s"
    season          = Column(String)          # e.g. "2023-24"
    team            = Column(String)

    # Shooting
    fg_pct          = Column(Float)
    three_pt_pct    = Column(Float)
    ts_pct          = Column(Float)

    # Ratings
    offensive_rating = Column(Float)
    defensive_rating = Column(Float)
    net_rating       = Column(Float)

    # Box stats (per 36 min)
    rebounds        = Column(Float)
    assists         = Column(Float)
    blocks          = Column(Float)
    steals          = Column(Float)
    points          = Column(Float)
    turnovers       = Column(Float)

    # Advanced
    usage_rate      = Column(Float)
    win_shares      = Column(Float)
    win_shares_per48 = Column(Float)
    bpm             = Column(Float)   # Box Plus/Minus
    vorp            = Column(Float)   # Value Over Replacement Player
    per             = Column(Float)   # Player Efficiency Rating

    # Role flags
    is_ball_handler  = Column(Boolean, default=False)
    is_rim_protector = Column(Boolean, default=False)
    is_three_point_specialist = Column(Boolean, default=False)

    # Games played — used to filter small sample sizes
    games_played     = Column(Integer, default=0)
    minutes_per_game = Column(Float, default=0.0)

    # Shot attempt totals — used to validate percentage stats
    fg_attempts      = Column(Integer, default=0)   # total FGA for the season
    three_pt_attempts = Column(Integer, default=0)  # total FG3A for the season
    ft_attempts      = Column(Integer, default=0)   # total FTA for the season

    # Position group from NBA.com (G/F/C) and secondary position
    position_group   = Column(String, default="")   # G, F, or C
    secondary_position = Column(String, default="") # e.g. SG when primary is PG


def get_engine():
    os.makedirs(os.path.join(os.path.dirname(__file__), "..", "data"), exist_ok=True)
    return create_engine(DATABASE_URL)


def get_session():
    engine = get_engine()
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def init_db():
    engine = get_engine()
    Base.metadata.create_all(engine)
    print("Database initialized.")
