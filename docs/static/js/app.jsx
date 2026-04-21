const { useState, useEffect, useRef } = React;

const LINEUP_LABELS = {
  best_shooting:  "Best Shooting",
  best_offense:   "Best Offense",
  best_defense:   "Best Defense",
  most_balanced:  "Most Balanced",
  small_ball:     "Small Ball",
  traditional:    "Traditional",
};

const ALL_POSITIONS = ["PG", "SG", "SF", "PF", "C"];

// ── Radar Chart ─────────────────────────────────────────────────────────────
function RadarChart({ players }) {
  const ref = useRef();
  useEffect(() => {
    if (!players || !players.length) return;
    const categories = ["PTS", "REB", "AST", "BLK", "STL", "3PT%"];
    const keys = ["points", "rebounds", "assists", "blocks", "steals", "three_pt_pct"];
    const colors = ["#1a1a1a","#5c6bc0","#7a7570","#b0aa9f","#ddd8ce"];

    const traces = players.map((p, i) => ({
      type: "scatterpolar",
      r: keys.map(k => parseFloat(p[k] || 0)),
      theta: categories,
      fill: "toself",
      name: p.name,
      line: { color: colors[i % colors.length] },
      fillcolor: colors[i % colors.length] + "33",
    }));

    Plotly.react(ref.current, traces, {
      polar: {
        bgcolor: "#faf7f2",
        radialaxis: { visible: true, color: "#b0aa9f", gridcolor: "#ddd8ce" },
        angularaxis: { color: "#7a7570", gridcolor: "#ddd8ce" },
      },
      paper_bgcolor: "#faf7f2",
      plot_bgcolor:  "#faf7f2",
      font: { color: "#1a1a1a", size: 11, family: "Inter, sans-serif" },
      legend: { font: { color: "#7a7570", size: 10 } },
      margin: { t: 20, b: 20, l: 20, r: 20 },
      showlegend: true,
    }, { responsive: true, displayModeBar: false });
  }, [players]);

  return <div ref={ref} style={{ height: 320 }} />;
}

// ── Efficiency Scatter ───────────────────────────────────────────────────────
function EfficiencyChart({ players }) {
  const ref = useRef();
  useEffect(() => {
    if (!players || !players.length) return;
    const trace = {
      type: "scatter",
      mode: "markers+text",
      x: players.map(p => p.offensive_rating),
      y: players.map(p => p.defensive_rating),
      text: players.map(p => p.name.split(" ").pop()),
      textposition: "top center",
      marker: {
        size: players.map(p => Math.max(10, (p.ts_pct || 0.5) * 40)),
        color: players.map(p => p.bpm || 0),
        colorscale: "RdYlGn",
        showscale: true,
        colorbar: { title: "BPM", tickfont: { color: "#7a7570" }, titlefont: { color: "#7a7570" } },
      },
      textfont: { color: "#1a1a1a", size: 10 },
    };

    Plotly.react(ref.current, [trace], {
      xaxis: { title: "Offensive Rating", color: "#7a7570", gridcolor: "#ddd8ce", zerolinecolor: "#ddd8ce" },
      yaxis: { title: "Defensive Rating (lower=better)", color: "#7a7570", gridcolor: "#ddd8ce", zerolinecolor: "#ddd8ce", autorange: "reversed" },
      paper_bgcolor: "#faf7f2",
      plot_bgcolor:  "#faf7f2",
      font: { color: "#1a1a1a", size: 11, family: "Inter, sans-serif" },
      margin: { t: 20, b: 50, l: 60, r: 20 },
    }, { responsive: true, displayModeBar: false });
  }, [players]);

  return <div ref={ref} style={{ height: 320 }} />;
}

// ── Shot Distribution Bar ────────────────────────────────────────────────────
function ShotChart({ players }) {
  const ref = useRef();
  useEffect(() => {
    if (!players || !players.length) return;
    const traces = [
      {
        type: "bar", name: "FG%",
        x: players.map(p => p.name.split(" ").pop()),
        y: players.map(p => parseFloat(p.fg_pct || 0) * 100),
        marker: { color: "#5c6bc0" },
      },
      {
        type: "bar", name: "3PT%",
        x: players.map(p => p.name.split(" ").pop()),
        y: players.map(p => parseFloat(p.three_pt_pct || 0) * 100),
        marker: { color: "#1a1a1a" },
      },
      {
        type: "bar", name: "TS%",
        x: players.map(p => p.name.split(" ").pop()),
        y: players.map(p => parseFloat(p.ts_pct || 0) * 100),
        marker: { color: "#b0aa9f" },
      },
    ];

    Plotly.react(ref.current, traces, {
      barmode: "group",
      xaxis: { color: "#7a7570", gridcolor: "#ddd8ce" },
      yaxis: { title: "%", color: "#7a7570", gridcolor: "#ddd8ce", range: [0, 80] },
      paper_bgcolor: "#faf7f2",
      plot_bgcolor:  "#faf7f2",
      font: { color: "#1a1a1a", size: 11, family: "Inter, sans-serif" },
      legend: { font: { color: "#7a7570" } },
      margin: { t: 10, b: 40, l: 50, r: 10 },
    }, { responsive: true, displayModeBar: false });
  }, [players]);

  return <div ref={ref} style={{ height: 280 }} />;
}

// ── Synergy Score Bar ────────────────────────────────────────────────────────
function SynergyChart({ players }) {
  const ref = useRef();
  useEffect(() => {
    if (!players || !players.length) return;
    const metrics = ["per", "bpm", "win_shares"];
    const labels  = ["PER", "BPM", "Win Shares"];
    const colors  = ["#1a1a1a", "#5c6bc0", "#b0aa9f"];

    const traces = metrics.map((m, i) => ({
      type: "bar",
      name: labels[i],
      x: players.map(p => p.name.split(" ").pop()),
      y: players.map(p => parseFloat(p[m] || 0)),
      marker: { color: colors[i] },
    }));

    Plotly.react(ref.current, traces, {
      barmode: "group",
      xaxis: { color: "#7a7570", gridcolor: "#ddd8ce" },
      yaxis: { color: "#7a7570", gridcolor: "#ddd8ce" },
      paper_bgcolor: "#faf7f2",
      plot_bgcolor:  "#faf7f2",
      font: { color: "#1a1a1a", size: 11, family: "Inter, sans-serif" },
      legend: { font: { color: "#7a7570" } },
      margin: { t: 10, b: 40, l: 50, r: 10 },
    }, { responsive: true, displayModeBar: false });
  }, [players]);

  return <div ref={ref} style={{ height: 280 }} />;
}

// ── Lineup Summary ──────────────────────────────────────────────────────────
function LineupSummary({ summary, lineupType }) {
  const [expanded, setExpanded] = React.useState(null);
  if (!summary) return null;

  return (
    <div className="summary-card">
      <h3>Why This Lineup Works</h3>

      <p className="summary-overall">{summary.overall}</p>

      {summary.synergy && (
        <div className="summary-synergy">
          <span>{summary.synergy}</span>
        </div>
      )}

      <div className="summary-players">
        <h4>Player Selection Breakdown</h4>
        {summary.players.map((p, i) => (
          <div key={i} className="summary-player">
            <button
              className={`summary-player-btn ${expanded === i ? 'open' : ''}`}
              onClick={() => setExpanded(expanded === i ? null : i)}
            >
              <span className="summary-player-name">{p.name}</span>
              <span className="summary-chevron">{expanded === i ? '▲' : '▼'}</span>
            </button>
            {expanded === i && (
              <div className="summary-player-body">
                <p>{p.reason}</p>
                {p.snubs && p.snubs.length > 0 && (
                  <div className="summary-snubs">
                    <strong>Notable omissions at this position:</strong>
                    {p.snubs.map((s, j) => (
                      <div key={j} className="snub-row">
                        <span className="snub-name">{s.name} ({s.season}) — {s.stat}</span>
                        <span className="snub-reason">{s.reason}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Player Card ──────────────────────────────────────────────────────────────
function PlayerCard({ player }) {
  return (
    <div className="player-card">
      <span className="player-pos">{player.position}</span>
      <div className="player-name">{player.name}</div>
      <div className="player-team">{player.team} · {player.season}</div>

      {[
        ["PTS", player.points],
        ["REB", player.rebounds],
        ["AST", player.assists],
        ["BLK", player.blocks],
        ["STL", player.steals],
        ["3PT%", player.three_pt_pct != null ? (player.three_pt_pct * 100).toFixed(1) + "%" : "N/A"],
        ["TS%",  player.ts_pct != null ? (player.ts_pct * 100).toFixed(1) + "%" : "N/A"],
        ["ORTG", player.offensive_rating ?? "N/A"],
        ["DRTG", player.defensive_rating ?? "N/A"],
        ["BPM",  player.bpm ?? "N/A"],
        ["PER",  player.per ?? "N/A"],
        ["WS",   player.win_shares ?? "N/A"],
      ].map(([lbl, val]) => (
        <div className="stat-row" key={lbl}>
          <span className="stat-label">{lbl}</span>
          <span className="stat-val">{val}</span>
        </div>
      ))}

      <div style={{ marginTop: 8 }}>
        {player.is_ball_handler           && <span className="badge">Handler</span>}
        {player.is_rim_protector          && <span className="badge">Rim</span>}
        {player.is_three_point_specialist && <span className="badge">3PT</span>}
      </div>
    </div>
  );
}

// ── Team Stats Bar ───────────────────────────────────────────────────────────
function TeamStats({ stats }) {
  const items = [
    ["ORTG",  stats.avg_offensive_rating],
    ["DRTG",  stats.avg_defensive_rating],
    ["REB",   stats.total_rebounds],
    ["AST",   stats.total_assists],
    ["BLK",   stats.total_blocks],
    ["WS",    stats.total_win_shares],
  ];
  return (
    <div className="team-stats">
      {items.map(([lbl, val]) => (
        <div className="stat-box" key={lbl}>
          <div className="val">{val}</div>
          <div className="lbl">{lbl}</div>
        </div>
      ))}
    </div>
  );
}

// ── Main App ─────────────────────────────────────────────────────────────────
function App() {
  const [lineupType, setLineupType]   = useState("most_balanced");
  const [era, setEra]                 = useState("");
  const [season, setSeason]           = useState("");
  const [positions, setPositions]     = useState([]);
  const [filters, setFilters]         = useState({ lineup_types: [], eras: [], seasons: [] });
  const [result, setResult]           = useState(null);
  const [loading, setLoading]         = useState(false);
  const [progress, setProgress]       = useState(0);
  const [progressMsg, setProgressMsg] = useState("");
  const [error, setError]             = useState("");
  const progressRef                   = useRef(null);

  useEffect(() => {
    api.filters()
      .then(r => r.json())
      .then(setFilters)
      .catch(err => console.error("Failed to load filters:", err));
  }, []);

  const togglePos = (pos) => {
    setPositions(prev =>
      prev.includes(pos) ? prev.filter(p => p !== pos) : [...prev, pos]
    );
  };

  const STEPS = [
    "Querying player database...",
    "Filtering by constraints...",
    "Scoring player pool...",
    "Evaluating lineup combinations...",
    "Applying synergy bonuses...",
    "Calculating win prediction...",
  ];

  const stepRef = useRef(0);

  const startProgress = () => {
    stepRef.current = 0;
    setProgress(5);
    setProgressMsg(STEPS[0]);
    progressRef.current = setInterval(() => {
      stepRef.current += 1;
      if (stepRef.current < STEPS.length) {
        const pct = Math.round((stepRef.current / STEPS.length) * 90);
        setProgress(pct);
        setProgressMsg(STEPS[stepRef.current]);
      }
      // Once all steps shown, just hold — don't go to 100
    }, 600);
  };

  const stopProgress = (cb) => {
    clearInterval(progressRef.current);
    progressRef.current = null;
    setProgress(100);
    setProgressMsg("Complete! ✓");
    // Small delay so user sees 100% before result renders
    setTimeout(cb, 300);
  };

  const generate = async () => {
    setLoading(true);
    setProgress(0);
    setError("");
    setResult(null);
    startProgress();
    try {
      const resp = await api.lineup({
        lineup_type: lineupType,
        era:         era || null,
        season:      season || null,
        positions:   positions.length ? positions : null,
      });
      const data = await resp.json();
      stopProgress(() => {
        setLoading(false);
        if (data.error) setError(data.error);
        else setResult(data);
      });
    } catch (e) {
      stopProgress(() => {
        setLoading(false);
        setError("Failed to connect to server. Make sure the backend is running.");
      });
    }
  };

  return (
    <>
      <header className="header">
        <div>
          <h1>NBA Lineup Optimizer</h1>
          <span>Data-driven lineup generation using real NBA statistics</span>
        </div>
      </header>

      <div className="layout">
        {/* ── Sidebar ── */}
        <aside className="sidebar">
          <div className="card">
            <h3>Lineup Type</h3>
            <div className="type-pills">
              {Object.entries(LINEUP_LABELS).map(([key, label]) => (
                <button
                  key={key}
                  className={`pill ${lineupType === key ? "active" : ""}`}
                  onClick={() => setLineupType(key)}
                >{label}</button>
              ))}
            </div>
          </div>

          <div className="card">
            <h3>Filters</h3>

            <label>Era</label>
            <select value={era} onChange={e => setEra(e.target.value)}>
              <option value="">All Eras</option>
              {filters.eras.map(e => <option key={e} value={e}>{e}</option>)}
            </select>

            <label>Season</label>
            <select value={season} onChange={e => setSeason(e.target.value)}>
              <option value="">All Seasons</option>
              {filters.seasons.map(s => <option key={s} value={s}>{s}</option>)}
            </select>

            <label>Positions (leave blank for all)</label>
            <div className="position-grid">
              {ALL_POSITIONS.map(pos => (
                <button
                  key={pos}
                  className={`pos-btn ${positions.includes(pos) ? "active" : ""}`}
                  onClick={() => togglePos(pos)}
                >{pos}</button>
              ))}
            </div>
          </div>

          <button className="btn-generate" onClick={generate} disabled={loading}>
            {loading ? "Generating..." : "Generate Lineup"}
          </button>
        </aside>

        {/* ── Main ── */}
        <main className="main">
          {error && <div className="error-msg">{error}</div>}

          {loading && (
            <div className="progress-container">
              <div className="progress-header">
                <span className="progress-label">{progressMsg}</span>
                <span className="progress-pct">{progress}%</span>
              </div>
              <div className="progress-track">
                <div className="progress-bar" style={{ width: `${progress}%` }} />
              </div>
              <div className="progress-steps">
                {STEPS.map((msg, idx) => (
                  <div key={idx} className={`progress-step ${progress >= Math.round((idx / STEPS.length) * 90) + 5 ? "done" : ""}`}>
                    <span className="step-dot" />
                    <span className="step-text">{msg}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {!loading && !result && !error && (
            <div className="empty-state">
              <div className="icon">—</div>
              <p>Select a lineup type and click <strong>Generate Lineup</strong> to get started.</p>
            </div>
          )}

          {result && (
            <>
              {/* Win prediction */}
              <div className="win-banner">
                <div className="wins">{result.team_stats.predicted_wins_82}W</div>
                <div className="desc">
                  <strong>Predicted record over 82 games</strong><br />
                  {(result.team_stats.predicted_win_pct * 100).toFixed(1)}% win rate ·
                  Lineup: {LINEUP_LABELS[result.lineup_type]}
                </div>
              </div>

              {/* Team stats */}
              <div className="card">
                <h3>Combined Team Metrics</h3>
                <TeamStats stats={result.team_stats} />
              </div>

              {/* Player cards */}
              <div className="card">
                <h3>The Starting Five</h3>
                <div className="players-grid">
                  {result.players.map((p, i) => <PlayerCard key={i} player={p} />)}
                </div>
              </div>

              {/* Lineup Summary */}
              {result.summary && (
                <LineupSummary summary={result.summary} lineupType={result.lineup_type} />
              )}

              {/* Charts */}
              <div className="charts-grid">
                <div className="chart-card">
                  <h4>Player Radar — Role Profiles</h4>
                  <RadarChart players={result.players} />
                </div>
                <div className="chart-card">
                  <h4>Offensive vs Defensive Rating</h4>
                  <EfficiencyChart players={result.players} />
                </div>
                <div className="chart-card">
                  <h4>Shot Distribution</h4>
                  <ShotChart players={result.players} />
                </div>
                <div className="chart-card">
                  <h4>Lineup Synergy Metrics</h4>
                  <SynergyChart players={result.players} />
                </div>
              </div>
            </>
          )}
        </main>
      </div>
    </>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
