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

// Markets
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

// Series definitions
export function getSeries(category, marketId) {
  const params = new URLSearchParams();
  if (category) params.append("category", category);
  if (marketId) params.append("market_id", marketId);
  return request(`/api/series/?${params}`);
}

export function createSeries(data) {
  return request("/api/series/", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// Time series data
export function getTimeSeriesData(seriesId, start, end) {
  const params = new URLSearchParams({ series_id: seriesId });
  if (start) params.append("start", start);
  if (end) params.append("end", end);
  return request(`/api/timeseries/?${params}`);
}

export function createTimeSeriesData(data) {
  return request("/api/timeseries/", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function createTimeSeriesDataBulk(dataPoints) {
  return request("/api/timeseries/bulk", {
    method: "POST",
    body: JSON.stringify({ data: dataPoints }),
  });
}

// Data sources
export function getDataSources() {
  return request("/api/data-sources/");
}

export function createDataSource(data) {
  return request("/api/data-sources/", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// Forecasts
export function getForecastTargets(marketId) {
  const params = new URLSearchParams();
  if (marketId) params.append("market_id", marketId);
  return request(`/api/forecasts/targets?${params}`);
}

export function createForecastTarget(data) {
  return request("/api/forecasts/targets", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function getForecastRuns(forecastTargetId) {
  return request(
    `/api/forecasts/runs?forecast_target_id=${forecastTargetId}`
  );
}

export function getForecastResults(forecastRunId) {
  return request(
    `/api/forecasts/results?forecast_run_id=${forecastRunId}`
  );
}

// Run forecast
export function runForecast(targetId) {
  return request(`/api/forecasts/run/${targetId}`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

// Dashboard
export function getDashboardSummary(marketId) {
  return request(`/api/dashboard/summary?market_id=${marketId}`);
}

export function getForecastAccuracy(forecastRunId) {
  return request(`/api/dashboard/accuracy?forecast_run_id=${forecastRunId}`);
}

// Health
export function getHealth() {
  return request("/api/health");
}
