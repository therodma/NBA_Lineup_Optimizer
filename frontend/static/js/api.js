// Central API config — change this one line if the port ever changes
const API_BASE = "http://127.0.0.1:8000";

async function fetchWithRetry(url, options = {}, retries = 3, delay = 3000) {
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

const api = {
  health:  () => fetchWithRetry(`${API_BASE}/api/health`),
  filters: () => fetchWithRetry(`${API_BASE}/api/filters`),
  lineup:  (body) => fetchWithRetry(`${API_BASE}/api/lineup`, {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify(body),
  }),
};
