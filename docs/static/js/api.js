const API_BASE = "https://nba-lineup-optimizer.onrender.com";

const api = {
  health:  () => fetch(`${API_BASE}/api/health`),
  filters: () => fetch(`${API_BASE}/api/filters`),
  lineup:  (body) => fetch(`${API_BASE}/api/lineup`, {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify(body),
  }),
};
