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
import { getPrices } from "../services/api";

export default function PriceChart({ market }) {
  const [prices, setPrices] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!market) return;
    setError(null);
    getPrices(market.id)
      .then((data) =>
        setPrices(
          data.map((p) => ({
            ...p,
            date: new Date(p.timestamp).toLocaleDateString(),
          }))
        )
      )
      .catch((err) => setError(err.message));
  }, [market]);

  if (!market) {
    return <p>Select a market to view prices.</p>;
  }

  if (error) {
    return <p className="error">Failed to load prices: {error}</p>;
  }

  if (prices.length === 0) {
    return <p>No price data available for {market.name}.</p>;
  }

  return (
    <div className="price-chart">
      <h2>
        {market.name} - Prices ({market.currency}/{market.unit})
      </h2>
      <ResponsiveContainer width="100%" height={400}>
        <LineChart data={prices}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis />
          <Tooltip />
          <Line
            type="monotone"
            dataKey="price"
            stroke="#2563eb"
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
