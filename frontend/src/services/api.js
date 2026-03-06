const API_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Request failed: ${response.status}`);
  }
  return response.json();
}

export function getMarkets() {
  return request("/api/markets/");
}

export function getMarket(id) {
  return request(`/api/markets/${id}`);
}

export function createMarket(data) {
  return request("/api/markets/", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function getPrices(marketId, start, end) {
  const params = new URLSearchParams({ market_id: marketId });
  if (start) params.append("start", start);
  if (end) params.append("end", end);
  return request(`/api/prices/?${params}`);
}

export function createPrices(prices) {
  return request("/api/prices/bulk", {
    method: "POST",
    body: JSON.stringify({ prices }),
  });
}
