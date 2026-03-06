import React, { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
  ComposedChart,
  Legend,
} from "recharts";
import { getSeries, getTimeSeriesData, getForecastResults } from "../services/api";

function formatDate(ts) {
  const d = new Date(ts);
  return d.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function PriceChart({ market, forecastRunId }) {
  const [data, setData] = useState([]);
  const [forecastData, setForecastData] = useState([]);
  const [seriesName, setSeriesName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Load actual price data for selected market
  useEffect(() => {
    if (!market) return;
    setError(null);
    setLoading(true);

    // Find the price series for this market
    getSeries("price", market.id)
      .then((seriesList) => {
        if (seriesList.length === 0) {
          setData([]);
          setSeriesName("");
          setLoading(false);
          return;
        }
        const series = seriesList[0];
        setSeriesName(series.name);
        return getTimeSeriesData(series.id);
      })
      .then((tsData) => {
        if (!tsData) return;
        setData(
          tsData.map((p) => ({
            timestamp: p.timestamp,
            date: formatDate(p.timestamp),
            value: p.value,
          }))
        );
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [market]);

  // Load forecast data if a run is selected
  useEffect(() => {
    if (!forecastRunId) {
      setForecastData([]);
      return;
    }
    getForecastResults(forecastRunId)
      .then((results) =>
        setForecastData(
          results.map((r) => ({
            timestamp: r.timestamp,
            date: formatDate(r.timestamp),
            forecast: r.value,
            lower: r.lower_bound,
            upper: r.upper_bound,
          }))
        )
      )
      .catch(() => setForecastData([]));
  }, [forecastRunId]);

  if (!market) {
    return <p>Select a market to view prices.</p>;
  }

  if (loading) {
    return <p>Loading data...</p>;
  }

  if (error) {
    return <p className="error">Failed to load data: {error}</p>;
  }

  if (data.length === 0 && forecastData.length === 0) {
    return <p>No price data available for {market.name}.</p>;
  }

  // Merge actual and forecast data on timestamp
  const hasForecast = forecastData.length > 0;
  let chartData;
  if (hasForecast) {
    const merged = new Map();
    for (const d of data) {
      merged.set(d.timestamp, { ...d });
    }
    for (const f of forecastData) {
      const existing = merged.get(f.timestamp) || { timestamp: f.timestamp, date: f.date };
      merged.set(f.timestamp, { ...existing, ...f });
    }
    chartData = Array.from(merged.values()).sort(
      (a, b) => new Date(a.timestamp) - new Date(b.timestamp)
    );
  } else {
    chartData = data;
  }

  return (
    <div className="price-chart">
      <h2>
        {market.name} - {seriesName || "Prices"} ({market.currency}/{market.unit})
      </h2>
      <ResponsiveContainer width="100%" height={400}>
        {hasForecast ? (
          <ComposedChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Line
              type="monotone"
              dataKey="value"
              stroke="#2563eb"
              strokeWidth={2}
              dot={false}
              name="Actual"
            />
            <Line
              type="monotone"
              dataKey="forecast"
              stroke="#f59e0b"
              strokeWidth={2}
              strokeDasharray="5 5"
              dot={false}
              name="Forecast"
            />
            <Area
              type="monotone"
              dataKey="upper"
              stroke="none"
              fill="#f59e0b"
              fillOpacity={0.1}
              name="Upper bound"
            />
            <Area
              type="monotone"
              dataKey="lower"
              stroke="none"
              fill="#f59e0b"
              fillOpacity={0.1}
              name="Lower bound"
            />
          </ComposedChart>
        ) : (
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip />
            <Line
              type="monotone"
              dataKey="value"
              stroke="#2563eb"
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        )}
      </ResponsiveContainer>
    </div>
  );
}
