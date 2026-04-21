# NBA Lineup Optimizer

A full-stack data science web app that scrapes real NBA statistics and generates optimal lineups using machine learning and combinatorial optimization.

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
This takes 15–30 minutes due to respectful rate limiting between requests.
```bash
python backend/scrapers/pipeline.py
```
This scrapes Basketball Reference (2016–⚠️ Failed to connect to server. Make sure the backend is running.2024) and NBA.com estimated metrics, then loads everything into `data/nba.db`.

### 3. Run the web server
```bash
python run.py
```
Open your browser at: **http://localhost:5000**

---

## Lineup Types

| Type | Description |
|------|-------------|
| Best Shooting | Maximizes 3PT%, TS%, FG% with spacing |
| Best Offense | Maximizes ORTG, PER, assists, efficiency |
| Best Defense | Minimizes DRTG, maximizes blocks/steals |
| Most Balanced | Optimizes BPM, win shares, two-way play |
| Small Ball | 4-guard/wing lineup, no traditional center |
| Traditional | True center, rebounding, rim protection |

---

## Optimization Algorithm

1. Query players from DB matching user filters (era, season, height, position)
2. Normalize all stat columns using MinMaxScaler
3. Score each player using weighted stat formula per lineup type
4. Build candidate pool (top 8–10 per position)
5. Evaluate all 5-player combinations from the pool
6. Apply hard constraints (ball handler, rim protector, min rebounds, min blocks)
7. Apply synergy bonuses (spacing, role diversity, usage balance)
8. Return highest-scoring valid lineup

### Win% Prediction
Uses net rating approximation:
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
| POST | `/api/chart/radar` | Radar chart data |
| POST | `/api/chart/efficiency` | Efficiency scatter data |

### POST /api/lineup
```json
{
  "lineup_type": "best_shooting",
  "era": "2020s",
  "season": "2023-24",
  "min_height": null,
  "max_height": null,
  "positions": ["PG", "SG", "SF"]
}
```

---

## Data Sources

- **Basketball Reference** — Advanced stats, per-36 stats (2016–2024)
- **NBA.com** — Estimated offensive/defensive ratings
- **ESPN** — Roster height/position data

---

## Tech Stack

- **Backend**: Python, Flask, SQLAlchemy, SQLite
- **Scraping**: BeautifulSoup, Requests
- **Analysis**: Pandas, NumPy, scikit-learn (MinMaxScaler)
- **Frontend**: React 18 (CDN), Plotly.js
- **Charts**: Radar, scatter, grouped bar charts
