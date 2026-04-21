import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from backend.models.optimizer import generate_lineup
from backend.models.database import get_session, Player
from backend.config import LINEUP_TYPES

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = Flask(
    __name__,
    template_folder=os.path.join(ROOT, "frontend", "templates"),
    static_folder=os.path.join(ROOT, "frontend", "static"),
)

CORS(app, resources={r"/*": {"origins": "*"}})


# ── Health check ─────────────────────────────────────────────────────────────

@app.route("/api/health")
def health():
    return jsonify({"status": "running", "port": 8000})


# ── Frontend ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


# ── Lineup generation ─────────────────────────────────────────────────────────

@app.route("/api/lineup", methods=["POST"])
def api_lineup():
    body        = request.get_json(force=True) or {}
    lineup_type = body.get("lineup_type", "most_balanced")
    era         = body.get("era") or None
    season      = body.get("season") or None
    min_height  = body.get("min_height")
    max_height  = body.get("max_height")
    positions   = body.get("positions") or None

    result = generate_lineup(
        lineup_type=lineup_type,
        era=era,
        season=season,
        min_height=int(min_height) if min_height else None,
        max_height=int(max_height) if max_height else None,
        positions=positions,
    )
    return jsonify(result)


# ── Filters ───────────────────────────────────────────────────────────────────

@app.route("/api/filters")
def api_filters():
    session = get_session()
    eras    = sorted(set(r[0] for r in session.query(Player.era).distinct().all() if r[0]))
    seasons = [r[0] for r in session.query(Player.season).distinct().order_by(Player.season).all() if r[0]]
    session.close()
    return jsonify({
        "lineup_types": LINEUP_TYPES,
        "eras":         eras,
        "seasons":      seasons,
        "positions":    ["PG", "SG", "SF", "PF", "C"],
    })


# ── Players ───────────────────────────────────────────────────────────────────

@app.route("/api/players")
def api_players():
    name   = request.args.get("name", "")
    season = request.args.get("season")
    pos    = request.args.get("position")
    limit  = int(request.args.get("limit", 50))

    session = get_session()
    q = session.query(Player)
    if name:
        q = q.filter(Player.name.ilike(f"%{name}%"))
    if season:
        q = q.filter(Player.season == season)
    if pos:
        q = q.filter(Player.position.contains(pos))

    players = q.limit(limit).all()
    session.close()

    return jsonify([{
        "name": p.name, "position": p.position, "season": p.season,
        "team": p.team, "per": p.per, "bpm": p.bpm,
        "win_shares": p.win_shares, "offensive_rating": p.offensive_rating,
        "defensive_rating": p.defensive_rating, "three_pt_pct": p.three_pt_pct,
        "ts_pct": p.ts_pct, "rebounds": p.rebounds, "assists": p.assists,
        "blocks": p.blocks, "steals": p.steals, "points": p.points,
    } for p in players])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False, use_reloader=False, threaded=True)
