# NBA Lineup Optimizer

A full-stack web app that uses real NBA statistics to generate optimal lineups across every season from 1996–97 to 2023–24.

🟢 **Live Demo:** [https://therodma.github.io/NBA_Lineup_Optimizer](https://therodma.github.io/NBA_Lineup_Optimizer)

🔗 **GitHub:** [https://github.com/therodma/NBA_Lineup_Optimizer](https://github.com/therodma/NBA_Lineup_Optimizer)

---

## Project Structure

```
nba_lineup_optimizer/
├── backend/
│   ├── config.py               # App settings, constraints, weights
│   ├── api/
│   │   └── app.py              # Flask API + frontend serving
│   ├── models/
│   │   ├── database.py         # SQLAlchemy models + DB init
│   │   └── optimizer.py        # Lineup optimization engine
│   └── scrapers/
│       ├── bbref_scraper.py    # Basketball Reference scraper
│       ├── nba_scraper.py      # NBA.com stats API
│       ├── espn_scraper.py     # ESPN roster data
│       └── pipeline.py         # Full data pipeline runner
├── data/
│   └── nba.db                  # SQLite database (auto-created)
├── frontend/
│   ├── templates/index.html    # React app shell
│   └── static/
│       ├── css/styles.css
│       └── js/app.jsx          # React + Plotly frontend
├── docs/                       # GitHub Pages deployment (mirrors frontend)
├── requirements.txt
└── run.py                      # App entry point
```

---

## Setup

### 1. Install dependencies
```bash
cd nba_lineup_optimizer
pip install -r requirements.txt
```

### 2. Scrape data and populate the database
Takes 15–30 minutes due to rate limiting between requests.
```bash
python backend/scrapers/pipeline.py
```

### 3. Run the web server
```bash
python run.py
```
Open your browser at: **http://localhost:8000**

---

## Features

- **6 lineup types** — Best Shooting, Best Offense, Best Defense, Most Balanced, Small Ball, Traditional
- **28 seasons** of data (1996–97 through 2023–24)
- **Era filter** — selecting an era searches across all seasons within it and ignores any specific season selection
- **Season filter** — pin results to a single season (disabled when an era is selected)
- **Position filter** — restrict the pool to specific positions
- **Why This Lineup Works** — per-player explanations with notable snubs at each position
- **4 charts** — Radar profiles, Offensive vs Defensive Rating scatter, Shot Distribution, Synergy Metrics
- **Win prediction** — projected record over 82 games based on net rating

---

## Lineup Types

| Type | Description |
|------|-------------|
| Best Shooting | Maximizes 3PT%, TS%, FG% and floor spacing |
| Best Offense | Maximizes ORTG, PER, scoring and playmaking |
| Best Defense | Minimizes DRTG, maximizes blocks and steals |
| Most Balanced | Optimizes BPM, win shares, two-way impact |
| Small Ball | Perimeter-heavy lineup, no traditional center |
| Traditional | True center, rebounding, rim protection |

---

## Optimization Algorithm

1. Query players from DB matching filters (era, season, position)
2. Apply per-lineup-type qualification filters (min MPG, usage, attempts)
3. Normalize stats and score each player using weighted formula
4. Build position pools (primary + secondary position eligibility)
5. Select best available player per slot, no repeats
6. Apply synergy bonuses (spacing, ball handler, rim protector)
7. Return lineup with team stats and win prediction

### Win% Prediction
```
wins = 41 + (avg_net_rating × 4.0)
win% = wins / 82
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/lineup` | Generate optimal lineup |
| GET | `/api/filters` | Available eras, seasons, positions |
| GET | `/api/players` | Search players |
| GET | `/api/health` | Server health check |

### POST /api/lineup
```json
{
  "lineup_type": "best_shooting",
  "era": "2020s",
  "season": null,
  "positions": ["PG", "SG", "SF"]
}
```
> Note: if `era` is set, `season` is ignored.

---

## Data Sources

- **Basketball Reference** — Per-game stats, advanced stats (1996–2024)
- **NBA.com** — Offensive/defensive ratings, net rating
- **ESPN** — Roster height and position data

---

## Tech Stack

- **Backend**: Python, Flask, SQLAlchemy, SQLite
- **Scraping**: BeautifulSoup, Requests
- **Analysis**: Pandas, NumPy
- **Frontend**: React 18 (CDN), Plotly.js
- **Hosting**: Render (backend), GitHub Pages (frontend)
