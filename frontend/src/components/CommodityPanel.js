import React, { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  Brush,
} from "recharts";
import { getSeries, getTimeSeriesData } from "../services/api";

const COMMODITY_COLORS = {
  "TTF Gas": "#ef4444",
  "Brent Crude": "#8b5cf6",
  "EUA Carbon": "#10b981",
  "Natural Gas Henry Hub": "#f59e0b",
  "API2 Coal": "#6366f1",
};

function getColor(name) {
  for (const [key, color] of Object.entries(COMMODITY_COLORS)) {
    if (name.includes(key)) return color;
  }
  return "#64748b";
}

function formatDate(ts) {
  const d = new Date(ts);
  return d.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

function CommodityCard({ series, latestValue, change24h }) {
  const changeColor = change24h > 0 ? "#16a34a" : change24h < 0 ? "#dc2626" : "#64748b";
  const changeSign = change24h > 0 ? "+" : "";

  return (
    <div className="commodity-card">
      <div className="commodity-card-header">
        <span className="commodity-name">{series.name}</span>
        <span className="commodity-unit">{series.unit}</span>
      </div>
      <div className="commodity-card-value">
        <span className="commodity-price">
          {latestValue != null ? latestValue.toFixed(2) : "--"}
        </span>
        {change24h != null && (
          <span className="commodity-change" style={{ color: changeColor }}>
            {changeSign}{change24h.toFixed(1)}%
          </span>
        )}
      </div>
    </div>
  );
}

export default function CommodityPanel() {
  const [commoditySeries, setCommoditySeries] = useState([]);
  const [selectedSeries, setSelectedSeries] = useState([]);
  const [chartData, setChartData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [latestValues, setLatestValues] = useState({});

  // Load all commodity series
  useEffect(() => {
    getSeries("commodity")
      .then((series) => {
        setCommoditySeries(series);
        // Auto-select first two
        if (series.length > 0) {
          setSelectedSeries(series.slice(0, 2).map((s) => s.id));
        }
      })
      .catch(() => setCommoditySeries([]));
  }, []);

  // Load chart data for selected series
  useEffect(() => {
    if (selectedSeries.length === 0) {
      setChartData([]);
      return;
    }

    setLoading(true);
    const end = new Date().toISOString();
    const start = new Date(Date.now() - 90 * 24 * 3600 * 1000).toISOString();

    Promise.all(
      selectedSeries.map((id) =>
        getTimeSeriesData(id, start, end).then((data) => ({ id, data }))
      )
    )
      .then((results) => {
        // Merge all series into a single dataset keyed by timestamp
        const merged = new Map();

        for (const { id, data } of results) {
          const series = commoditySeries.find((s) => s.id === id);
          const colName = series ? series.name : `Series ${id}`;

          // Track latest values
          if (data.length > 0) {
            const latest = data[data.length - 1];
            const prev24h = data.find(
              (d) =>
                new Date(d.timestamp).getTime() <=
                new Date(latest.timestamp).getTime() - 24 * 3600 * 1000
            );
            const change =
              prev24h && prev24h.value !== 0
                ? ((latest.value - prev24h.value) / Math.abs(prev24h.value)) * 100
                : null;
            setLatestValues((prev) => ({
              ...prev,
              [id]: { value: latest.value, change },
            }));
          }

          // Only use daily (not hourly) for the chart to keep it clean
          const dailyMap = new Map();
          for (const d of data) {
            const dateKey = d.timestamp.split("T")[0];
            if (!dailyMap.has(dateKey)) {
              dailyMap.set(dateKey, d);
            }
          }

          for (const [dateKey, d] of dailyMap) {
            const existing = merged.get(dateKey) || {
              date: formatDate(d.timestamp),
              ts: new Date(d.timestamp).getTime(),
            };
            existing[colName] = d.value;
            merged.set(dateKey, existing);
          }
        }

        const sorted = Array.from(merged.values()).sort((a, b) => a.ts - b.ts);
        setChartData(sorted);
      })
      .catch(() => setChartData([]))
      .finally(() => setLoading(false));
  }, [selectedSeries, commoditySeries]);

  const toggleSeries = (id) => {
    setSelectedSeries((prev) =>
      prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id]
    );
  };

  if (commoditySeries.length === 0) {
    return (
      <div className="commodity-panel">
        <h3>Commodity Prices</h3>
        <p className="muted">No commodity data available yet. Data will appear after the first ingestion run.</p>
      </div>
    );
  }

  return (
    <div className="commodity-panel">
      <h3>Commodity & Fuel Prices</h3>
      <p className="muted" style={{ marginBottom: "1rem" }}>
        Key fuel and carbon prices that drive electricity costs
      </p>

      {/* Summary cards */}
      <div className="commodity-cards">
        {commoditySeries.map((s) => (
          <CommodityCard
            key={s.id}
            series={s}
            latestValue={latestValues[s.id]?.value}
            change24h={latestValues[s.id]?.change}
          />
        ))}
      </div>

      {/* Series selector chips */}
      <div className="commodity-selector">
        {commoditySeries.map((s) => (
          <button
            key={s.id}
            className={`series-chip ${selectedSeries.includes(s.id) ? "active" : ""}`}
            onClick={() => toggleSeries(s.id)}
            style={
              selectedSeries.includes(s.id)
                ? { borderColor: getColor(s.name), color: getColor(s.name) }
                : {}
            }
          >
            {s.name}
          </button>
        ))}
      </div>

      {/* Chart */}
      {loading ? (
        <p className="muted">Loading chart...</p>
      ) : chartData.length > 0 ? (
        <div className="commodity-chart">
          <ResponsiveContainer width="100%" height={350}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} minTickGap={40} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Legend />
              {selectedSeries.map((id) => {
                const s = commoditySeries.find((s) => s.id === id);
                if (!s) return null;
                return (
                  <Line
                    key={id}
                    type="monotone"
                    dataKey={s.name}
                    stroke={getColor(s.name)}
                    strokeWidth={2}
                    dot={false}
                    connectNulls
                  />
                );
              })}
              <Brush
                dataKey="date"
                height={25}
                stroke="#cbd5e1"
                fill="#f8fafc"
                tickFormatter={() => ""}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <p className="muted">Select commodity series to view chart.</p>
      )}
    </div>
  );
}
