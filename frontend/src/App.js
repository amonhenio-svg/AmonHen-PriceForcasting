import React, { useState } from "react";
import Layout from "./components/Layout";
import LandingPage from "./components/LandingPage";
import MarketList from "./components/MarketList";
import PriceChart from "./components/PriceChart";
import ForecastPanel from "./components/ForecastPanel";
import SeriesExplorer from "./components/SeriesExplorer";
import CommodityPanel from "./components/CommodityPanel";
import "./App.css";

function Dashboard() {
  const [selectedMarket, setSelectedMarket] = useState(null);
  const [selectedRunId, setSelectedRunId] = useState(null);
  const [selectedTarget, setSelectedTarget] = useState(null);
  const [activeTab, setActiveTab] = useState("prices");

  const handleMarketSelect = (market) => {
    setSelectedMarket(market);
    setSelectedRunId(null);
    setSelectedTarget(null);
  };

  return (
    <div className="app-content">
      <aside className="sidebar">
        <MarketList
          onSelectMarket={handleMarketSelect}
          selectedMarketId={selectedMarket?.id}
        />
      </aside>
      <section className="main-panel">
        <div className="tab-bar">
          <button
            className={`tab ${activeTab === "prices" ? "active" : ""}`}
            onClick={() => setActiveTab("prices")}
          >
            Prices
          </button>
          <button
            className={`tab ${activeTab === "commodities" ? "active" : ""}`}
            onClick={() => setActiveTab("commodities")}
          >
            Commodities
          </button>
          {selectedMarket && (
            <button
              className={`tab ${activeTab === "series" ? "active" : ""}`}
              onClick={() => setActiveTab("series")}
            >
              Data Series
            </button>
          )}
        </div>

        {activeTab === "prices" && (
          <>
            <PriceChart
              market={selectedMarket}
              forecastRunId={selectedRunId}
              forecastHorizonHours={selectedTarget?.horizon_hours}
            />
            <ForecastPanel
              market={selectedMarket}
              onSelectRun={setSelectedRunId}
              selectedRunId={selectedRunId}
              onTargetChange={setSelectedTarget}
            />
          </>
        )}

        {activeTab === "commodities" && <CommodityPanel />}

        {activeTab === "series" && (
          <SeriesExplorer market={selectedMarket} />
        )}
      </section>
    </div>
  );
}

function App() {
  const [page, setPage] = useState("landing");

  const handleNavigate = (target) => {
    setPage(target);
    window.scrollTo(0, 0);
  };

  return (
    <Layout page={page} onNavigate={handleNavigate}>
      {page === "landing" && <LandingPage onNavigate={handleNavigate} />}
      {page === "dashboard" && <Dashboard />}
      {page === "signup" && (
        <div className="signup-page">
          <div className="signup-card">
            <h2>Get Started</h2>
            <p>
              We're currently onboarding early customers. Leave your email and
              we'll set up your account.
            </p>
            <form
              className="signup-form"
              onSubmit={(e) => {
                e.preventDefault();
                alert(
                  "Thanks! We'll be in touch shortly to set up your account."
                );
              }}
            >
              <input
                type="text"
                placeholder="Company name"
                required
                className="signup-input"
              />
              <input
                type="email"
                placeholder="Work email"
                required
                className="signup-input"
              />
              <select className="signup-input" defaultValue="">
                <option value="" disabled>
                  How do you plan to use forecasts?
                </option>
                <option>Energy trading</option>
                <option>Procurement / purchasing</option>
                <option>Portfolio management</option>
                <option>Research / analytics</option>
                <option>Other</option>
              </select>
              <button type="submit" className="btn btn-primary btn-lg">
                Request Access
              </button>
            </form>
            <p className="signup-note">
              Free tier available. No credit card required.
            </p>
          </div>
        </div>
      )}
    </Layout>
  );
}

export default App;
