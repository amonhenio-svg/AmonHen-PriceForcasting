import React, { useEffect, useState } from "react";
import { getMarkets } from "../services/api";

const TYPE_LABELS = {
  day_ahead: "Day-Ahead",
  intraday: "Intraday",
  reserve: "Reserve",
};

export default function MarketList({ onSelectMarket, selectedMarketId }) {
  const [markets, setMarkets] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    getMarkets()
      .then(setMarkets)
      .catch((err) => setError(err.message));
  }, []);

  if (error) {
    return <p className="error">Failed to load markets: {error}</p>;
  }

  if (markets.length === 0) {
    return <p>No markets configured yet. Add markets via the API.</p>;
  }

  return (
    <div className="market-list">
      <h2>Markets</h2>
      <ul>
        {markets.map((market) => (
          <li
            key={market.id}
            className={market.id === selectedMarketId ? "selected" : ""}
            onClick={() => onSelectMarket(market)}
          >
            <strong>{market.name}</strong>
            <span>
              {market.country} &middot;{" "}
              {TYPE_LABELS[market.market_type] || market.market_type} &middot;{" "}
              {market.currency}/{market.unit}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
