import React, { useState } from "react";
import Layout from "./components/Layout";
import MarketList from "./components/MarketList";
import PriceChart from "./components/PriceChart";
import ForecastPanel from "./components/ForecastPanel";
import SeriesExplorer from "./components/SeriesExplorer";
import "./App.css";

function App() {
  const [selectedMarket, setSelectedMarket] = useState(null);
  const [selectedRunId, setSelectedRunId] = useState(null);
  const [activeTab, setActiveTab] = useState("prices");

  const handleMarketSelect = (market) => {
    setSelectedMarket(market);
    setSelectedRunId(null);
  };

  return (
    <Layout>
      <div className="app-content">
        <aside className="sidebar">
          <MarketList
            onSelectMarket={handleMarketSelect}
            selectedMarketId={selectedMarket?.id}
          />
        </aside>
        <section className="main-panel">
          {selectedMarket && (
            <div className="tab-bar">
              <button
                className={`tab ${activeTab === "prices" ? "active" : ""}`}
                onClick={() => setActiveTab("prices")}
              >
                Prices
              </button>
              <button
                className={`tab ${activeTab === "series" ? "active" : ""}`}
                onClick={() => setActiveTab("series")}
              >
                Data Series
              </button>
            </div>
          )}

          {activeTab === "prices" && (
            <>
              <PriceChart
                market={selectedMarket}
                forecastRunId={selectedRunId}
              />
              <ForecastPanel
                market={selectedMarket}
                onSelectRun={setSelectedRunId}
                selectedRunId={selectedRunId}
              />
            </>
          )}

          {activeTab === "series" && (
            <SeriesExplorer market={selectedMarket} />
          )}
        </section>
      </div>
    </Layout>
  );
}

export default App;
