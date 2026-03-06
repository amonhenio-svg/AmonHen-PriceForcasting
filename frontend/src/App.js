import React, { useState } from "react";
import Layout from "./components/Layout";
import MarketList from "./components/MarketList";
import PriceChart from "./components/PriceChart";
import "./App.css";

function App() {
  const [selectedMarket, setSelectedMarket] = useState(null);

  return (
    <Layout>
      <div className="app-content">
        <aside className="sidebar">
          <MarketList
            onSelectMarket={setSelectedMarket}
            selectedMarketId={selectedMarket?.id}
          />
        </aside>
        <section className="main-panel">
          <PriceChart market={selectedMarket} />
        </section>
      </div>
    </Layout>
  );
}

export default App;
