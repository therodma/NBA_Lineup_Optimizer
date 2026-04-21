// Central API config — change this one line if the port ever changes
const API_BASE = "http://127.0.0.1:8000";

const api = {
  health:  () => fetch(`${API_BASE}/api/health`),
  filters: () => fetch(`${API_BASE}/api/filters`),
  lineup:  (body) => fetch(`${API_BASE}/api/lineup`, {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify(body),
  }),
};
