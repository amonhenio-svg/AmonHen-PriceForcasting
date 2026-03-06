import React from "react";

export default function Layout({ children }) {
  return (
    <div className="app-layout">
      <header className="app-header">
        <h1>AmonHen Price Forecasting</h1>
        <p>European Energy Markets</p>
      </header>
      <main className="app-main">{children}</main>
    </div>
  );
}
