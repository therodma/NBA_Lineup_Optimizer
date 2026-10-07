const API_BASE = "https://nba-lineup-optimizer.onrender.com";

async function fetchWithRetry(url, options = {}, retries = 8, delay = 6000) {
  for (let i = 0; i < retries; i++) {
    try {
      const res = await fetch(url, options);
      if (res.ok || res.status < 500) return res;
    } catch (e) {
      if (i === retries - 1) throw e;
    }
    await new Promise(r => setTimeout(r, delay));
  }
}

async function wakeServer(onWaking) {
  // Ping health until the server responds, up to 60s
  for (let i = 0; i < 12; i++) {
    try {
      const res = await fetch(`${API_BASE}/api/health`);
      if (res.ok) return true;
    } catch (e) {}
    if (i === 0) onWaking();
    await new Promise(r => setTimeout(r, 5000));
  }
  return false;
}

const api = {
  health:  () => fetchWithRetry(`${API_BASE}/api/health`),
  filters: () => fetchWithRetry(`${API_BASE}/api/filters`),
  lineup:  (body) => fetchWithRetry(`${API_BASE}/api/lineup`, {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify(body),
  }),
  wakeServer,
};
