import React, { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { getSeries, getTimeSeriesData } from "../services/api";

const CATEGORY_COLORS = {
  price: "#2563eb",
  load: "#16a34a",
  generation: "#9333ea",
  weather: "#ea580c",
  commodity: "#dc2626",
};

export default function SeriesExplorer({ market }) {
  const [allSeries, setAllSeries] = useState([]);
  const [selectedSeries, setSelectedSeries] = useState(null);
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!market) {
      setAllSeries([]);
      return;
    }
    getSeries(null, market.id).then(setAllSeries).catch(() => setAllSeries([]));
  }, [market]);

  useEffect(() => {
    if (!selectedSeries) {
      setData([]);
      return;
    }
    setLoading(true);
    getTimeSeriesData(selectedSeries.id)
      .then((tsData) =>
        setData(
          tsData.map((p) => ({
            date: new Date(p.timestamp).toLocaleDateString(undefined, {
              month: "short",
              day: "numeric",
              hour: "2-digit",
            }),
            value: p.value,
          }))
        )
      )
      .catch(() => setData([]))
      .finally(() => setLoading(false));
  }, [selectedSeries]);

  if (!market) return null;

  // Group series by category
  const grouped = {};
  for (const s of allSeries) {
    if (!grouped[s.category]) grouped[s.category] = [];
    grouped[s.category].push(s);
  }

  return (
    <div className="series-explorer">
      <h3>Data Series</h3>
      {allSeries.length === 0 ? (
        <p className="muted">No data series available for this market.</p>
      ) : (
        <div className="series-categories">
          {Object.entries(grouped).map(([category, seriesList]) => (
            <div key={category} className="category-group">
              <h4 className="category-label">{category}</h4>
              <div className="series-chips">
                {seriesList.map((s) => (
                  <button
                    key={s.id}
                    className={`series-chip ${
                      s.id === selectedSeries?.id ? "active" : ""
                    }`}
                    style={{
                      borderColor:
                        s.id === selectedSeries?.id
                          ? CATEGORY_COLORS[category] || "#64748b"
                          : undefined,
                    }}
                    onClick={() => setSelectedSeries(s)}
                  >
                    {s.name}
                    <span className="series-unit">{s.unit}</span>
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {loading && <p>Loading...</p>}

      {selectedSeries && data.length > 0 && (
        <div className="series-chart">
          <h4>
            {selectedSeries.name} ({selectedSeries.unit})
          </h4>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Line
                type="monotone"
                dataKey="value"
                stroke={
                  CATEGORY_COLORS[selectedSeries.category] || "#64748b"
                }
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
