import React, { useEffect, useState, useCallback, useRef } from "react";
import {
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
  ComposedChart,
  Legend,
  Brush,
  ReferenceArea,
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

function formatShort(ts) {
  const d = new Date(ts);
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload || payload.length === 0) return null;
  const items = payload.filter((p) => p.value != null && p.name);
  return (
    <div className="chart-tooltip">
      <p className="chart-tooltip-label">{label}</p>
      {items.map((p) => (
        <p key={p.dataKey} style={{ color: p.color }}>
          {p.name}: <strong>{Number(p.value).toFixed(2)}</strong>
        </p>
      ))}
    </div>
  );
}

// Time range presets
const RANGES = [
  { label: "24h", hours: 24 },
  { label: "7d", hours: 168 },
  { label: "30d", hours: 720 },
  { label: "90d", hours: 2160 },
  { label: "All", hours: null },
];

export default function PriceChart({ market, forecastRunId }) {
  const [allData, setAllData] = useState([]);
  const [forecastData, setForecastData] = useState([]);
  const [seriesName, setSeriesName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeRange, setActiveRange] = useState("30d");

  // Drag-to-zoom state
  const [refAreaLeft, setRefAreaLeft] = useState(null);
  const [refAreaRight, setRefAreaRight] = useState(null);
  const [zoomLeft, setZoomLeft] = useState(null);
  const [zoomRight, setZoomRight] = useState(null);
  const isDragging = useRef(false);

  // Load actual price data for selected market
  useEffect(() => {
    if (!market) return;
    setError(null);
    setLoading(true);

    getSeries("price", market.id)
      .then((seriesList) => {
        if (seriesList.length === 0) {
          setAllData([]);
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
        setAllData(
          tsData.map((p) => ({
            timestamp: p.timestamp,
            date: formatDate(p.timestamp),
            dateShort: formatShort(p.timestamp),
            value: p.value,
            ts: new Date(p.timestamp).getTime(),
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
            dateShort: formatShort(r.timestamp),
            forecast: r.value,
            lower: r.lower_bound,
            upper: r.upper_bound,
            ts: new Date(r.timestamp).getTime(),
          }))
        )
      )
      .catch(() => setForecastData([]));
  }, [forecastRunId]);

  // Apply time range filter
  const getFilteredData = useCallback(() => {
    const range = RANGES.find((r) => r.label === activeRange);
    let filtered = allData;
    if (range && range.hours && allData.length > 0) {
      const cutoff = Date.now() - range.hours * 3600 * 1000;
      filtered = allData.filter((d) => d.ts >= cutoff);
    }
    return filtered;
  }, [allData, activeRange]);

  // Merge actual and forecast data
  const chartData = React.useMemo(() => {
    const filtered = getFilteredData();
    const hasForecast = forecastData.length > 0;
    if (!hasForecast) return filtered;

    const merged = new Map();
    for (const d of filtered) {
      merged.set(d.timestamp, { ...d });
    }
    for (const f of forecastData) {
      const existing = merged.get(f.timestamp) || {
        timestamp: f.timestamp,
        date: f.date,
        dateShort: f.dateShort,
        ts: f.ts,
      };
      merged.set(f.timestamp, { ...existing, ...f });
    }
    return Array.from(merged.values()).sort((a, b) => a.ts - b.ts);
  }, [getFilteredData, forecastData]);

  // Apply zoom filtering
  const displayData = React.useMemo(() => {
    if (zoomLeft == null || zoomRight == null) return chartData;
    return chartData.filter((d) => d.ts >= zoomLeft && d.ts <= zoomRight);
  }, [chartData, zoomLeft, zoomRight]);

  // Zoom handlers — drag to select, release to zoom
  const handleMouseDown = (e) => {
    if (e && e.activeLabel) {
      setRefAreaLeft(e.activeLabel);
      isDragging.current = true;
    }
  };
  const handleMouseMove = (e) => {
    if (isDragging.current && e && e.activeLabel) {
      setRefAreaRight(e.activeLabel);
    }
  };
  const handleMouseUp = () => {
    if (!isDragging.current) return;
    isDragging.current = false;

    if (refAreaLeft && refAreaRight && refAreaLeft !== refAreaRight) {
      const leftItem = chartData.find((d) => d.date === refAreaLeft);
      const rightItem = chartData.find((d) => d.date === refAreaRight);
      if (leftItem && rightItem) {
        const left = Math.min(leftItem.ts, rightItem.ts);
        const right = Math.max(leftItem.ts, rightItem.ts);
        setZoomLeft(left);
        setZoomRight(right);
      }
    }
    setRefAreaLeft(null);
    setRefAreaRight(null);
  };

  const resetZoom = () => {
    setZoomLeft(null);
    setZoomRight(null);
  };

  const handleRangeChange = (label) => {
    setActiveRange(label);
    resetZoom();
  };

  if (!market) {
    return (
      <div className="price-chart price-chart-empty">
        <p>Select a market to view prices.</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="price-chart">
        <p>Loading data...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="price-chart">
        <p className="error">Failed to load data: {error}</p>
      </div>
    );
  }

  if (allData.length === 0 && forecastData.length === 0) {
    return (
      <div className="price-chart">
        <p>No price data available for {market.name}. Data may still be loading.</p>
      </div>
    );
  }

  const hasForecast = forecastData.length > 0;

  return (
    <div className="price-chart">
      <div className="chart-header">
        <div className="chart-title-row">
          <h2>
            {market.name} - {seriesName || "Prices"} ({market.currency}/
            {market.unit})
          </h2>
          {zoomLeft != null && (
            <button className="zoom-reset-btn" onClick={resetZoom}>
              Reset Zoom
            </button>
          )}
        </div>
        <div className="chart-controls">
          <div className="range-selector">
            {RANGES.map((r) => (
              <button
                key={r.label}
                className={`range-btn ${activeRange === r.label ? "active" : ""}`}
                onClick={() => handleRangeChange(r.label)}
              >
                {r.label}
              </button>
            ))}
          </div>
          <span className="chart-hint">
            {zoomLeft == null ? "Drag on chart to zoom" : ""}
          </span>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={420}>
        <ComposedChart
          data={displayData}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          style={{ cursor: "crosshair" }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 11 }}
            interval="preserveStartEnd"
            minTickGap={60}
          />
          <YAxis
            tick={{ fontSize: 11 }}
            domain={["auto", "auto"]}
            tickFormatter={(v) => v.toFixed(0)}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend />

          {hasForecast && (
            <Area
              type="monotone"
              dataKey="upper"
              stroke="none"
              fill="#f59e0b"
              fillOpacity={0.12}
              name="Confidence Band"
              legendType="none"
            />
          )}
          {hasForecast && (
            <Area
              type="monotone"
              dataKey="lower"
              stroke="none"
              fill="#ffffff"
              fillOpacity={1}
              name=""
              legendType="none"
            />
          )}

          <Line
            type="monotone"
            dataKey="value"
            stroke="#2563eb"
            strokeWidth={1.5}
            dot={false}
            name="Actual"
            connectNulls={false}
          />

          {hasForecast && (
            <Line
              type="monotone"
              dataKey="forecast"
              stroke="#f59e0b"
              strokeWidth={2}
              strokeDasharray="6 3"
              dot={false}
              name="Forecast"
            />
          )}

          {/* Drag-to-zoom selection overlay */}
          {refAreaLeft && refAreaRight && (
            <ReferenceArea
              x1={refAreaLeft}
              x2={refAreaRight}
              strokeOpacity={0.3}
              fill="#2563eb"
              fillOpacity={0.1}
            />
          )}

          <Brush
            dataKey="dateShort"
            height={30}
            stroke="#cbd5e1"
            fill="#f8fafc"
            tickFormatter={() => ""}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
