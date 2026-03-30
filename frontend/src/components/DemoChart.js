import React, { useMemo } from "react";
import {
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";

// Generate realistic Day-Ahead price data with daily seasonality
function generateDemoData() {
  const data = [];
  const now = new Date();
  // Start 3 days ago
  const start = new Date(now);
  start.setDate(start.getDate() - 3);
  start.setHours(0, 0, 0, 0);

  const forecastStart = new Date(now);
  forecastStart.setHours(forecastStart.getHours() + 1, 0, 0, 0);

  // Base price around 85 EUR/MWh
  let base = 85;
  const seed = start.getDate();

  for (let h = 0; h < 4 * 24; h++) {
    const t = new Date(start);
    t.setHours(t.getHours() + h);
    const hour = t.getHours();

    // Daily pattern: low at night, peak morning & evening
    const dailyPattern =
      -12 * Math.cos((2 * Math.PI * (hour - 2)) / 24) +
      6 * Math.cos((4 * Math.PI * (hour - 8)) / 24);

    // Some day-to-day drift
    const dayDrift = 3 * Math.sin((2 * Math.PI * (h + seed)) / 72);

    // Noise
    const noise = (Math.sin(h * 137.5 + seed * 7) * 10000) % 8 - 4;

    const price = base + dailyPattern + dayDrift + noise;
    const isForecast = t >= forecastStart;

    const point = {
      timestamp: t.toISOString(),
      hour: t.toLocaleString(undefined, {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      }),
    };

    if (!isForecast) {
      point.actual = Math.round(price * 100) / 100;
    } else {
      const forecastNoise = (Math.sin(h * 43.7 + seed * 3) * 10000) % 3 - 1.5;
      const fc = price + forecastNoise;
      point.forecast = Math.round(fc * 100) / 100;
      point.upper = Math.round((fc + 8 + h * 0.05) * 100) / 100;
      point.lower = Math.round((fc - 8 - h * 0.05) * 100) / 100;
    }

    data.push(point);
  }

  return { data, forecastStartLabel: forecastStart.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })};
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload || payload.length === 0) return null;
  return (
    <div className="demo-tooltip">
      <p className="demo-tooltip-label">{label}</p>
      {payload.map((entry) => (
        <p key={entry.name} style={{ color: entry.color }}>
          {entry.name}: {entry.value?.toFixed(2)} EUR/MWh
        </p>
      ))}
    </div>
  );
}

export default function DemoChart() {
  const { data, forecastStartLabel } = useMemo(() => generateDemoData(), []);

  return (
    <div className="demo-chart-wrapper">
      <div className="demo-chart-header">
        <div>
          <h3>Germany Day-Ahead Electricity</h3>
          <span className="demo-chart-subtitle">
            Hourly prices &middot; EUR/MWh &middot; Live demo
          </span>
        </div>
        <div className="demo-chart-legend-custom">
          <span className="legend-item">
            <span className="legend-dot" style={{ background: "#2563eb" }} />
            Actual
          </span>
          <span className="legend-item">
            <span className="legend-dot" style={{ background: "#f59e0b" }} />
            Forecast
          </span>
          <span className="legend-item">
            <span
              className="legend-dot"
              style={{ background: "#f59e0b", opacity: 0.3 }}
            />
            Confidence Band
          </span>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={380}>
        <ComposedChart data={data} margin={{ top: 10, right: 20, bottom: 10, left: 10 }}>
          <defs>
            <linearGradient id="bandGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#f59e0b" stopOpacity={0.15} />
              <stop offset="100%" stopColor="#f59e0b" stopOpacity={0.05} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis
            dataKey="hour"
            tick={{ fontSize: 11, fill: "#94a3b8" }}
            interval={11}
            axisLine={{ stroke: "#e2e8f0" }}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 11, fill: "#94a3b8" }}
            axisLine={false}
            tickLine={false}
            domain={["auto", "auto"]}
            tickFormatter={(v) => `${v}`}
            label={{
              value: "EUR/MWh",
              angle: -90,
              position: "insideLeft",
              offset: 0,
              style: { fontSize: 11, fill: "#94a3b8" },
            }}
          />
          <Tooltip content={<CustomTooltip />} />
          <ReferenceLine
            x={forecastStartLabel}
            stroke="#94a3b8"
            strokeDasharray="4 4"
            label={{
              value: "Now",
              position: "top",
              fill: "#64748b",
              fontSize: 11,
            }}
          />
          <Area
            type="monotone"
            dataKey="upper"
            stroke="none"
            fill="url(#bandGradient)"
            isAnimationActive={false}
          />
          <Area
            type="monotone"
            dataKey="lower"
            stroke="none"
            fill="white"
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="actual"
            stroke="#2563eb"
            strokeWidth={2}
            dot={false}
            name="Actual"
            connectNulls={false}
          />
          <Line
            type="monotone"
            dataKey="forecast"
            stroke="#f59e0b"
            strokeWidth={2}
            strokeDasharray="6 3"
            dot={false}
            name="Forecast"
            connectNulls={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
