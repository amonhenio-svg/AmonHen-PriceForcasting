import React from "react";

export default function Layout({ children, page, onNavigate }) {
  return (
    <div className="app-layout">
      <header className="app-header">
        <div className="header-inner">
          <div
            className="header-brand"
            onClick={() => onNavigate("landing")}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => e.key === "Enter" && onNavigate("landing")}
          >
            <h1>AmonHen</h1>
            <p>Price Forecasting</p>
          </div>
          <nav className="header-nav">
            <button
              className={page === "landing" ? "active" : ""}
              onClick={() => onNavigate("landing")}
            >
              Home
            </button>
            <button
              className={page === "dashboard" ? "active" : ""}
              onClick={() => onNavigate("dashboard")}
            >
              Dashboard
            </button>
            <button
              className="nav-cta"
              onClick={() => onNavigate("signup")}
            >
              Get Started
            </button>
          </nav>
        </div>
      </header>
      <main className={page === "landing" ? "" : "app-main"}>{children}</main>
    </div>
  );
}
