import React from "react";
import DemoChart from "./DemoChart";

const MARKETS = [
  {
    name: "Germany Day-Ahead",
    country: "DE",
    type: "Day-Ahead",
    status: "live",
    description: "EPEX Spot hourly auction prices",
  },
  {
    name: "France Day-Ahead",
    country: "FR",
    type: "Day-Ahead",
    status: "coming",
    description: "EPEX Spot hourly auction prices",
  },
  {
    name: "Netherlands Day-Ahead",
    country: "NL",
    type: "Day-Ahead",
    status: "coming",
    description: "EPEX Spot hourly auction prices",
  },
  {
    name: "Nordic Day-Ahead",
    country: "Nordics",
    type: "Day-Ahead",
    status: "coming",
    description: "Nord Pool system & area prices",
  },
];

const TIERS = [
  {
    name: "Explorer",
    price: "Free",
    priceDetail: "No credit card required",
    features: [
      "1 market (Germany Day-Ahead)",
      "24-hour forecast horizon",
      "Daily CSV download",
      "Accuracy dashboard",
    ],
    cta: "Start Free",
    highlighted: false,
  },
  {
    name: "Professional",
    price: "\u20ac149",
    priceDetail: "per month",
    features: [
      "All available markets",
      "7-day forecast horizon",
      "API access (10k calls/mo)",
      "Hourly granularity",
      "Confidence intervals",
      "Email support",
    ],
    cta: "Start Trial",
    highlighted: true,
  },
  {
    name: "Enterprise",
    price: "Custom",
    priceDetail: "tailored to your needs",
    features: [
      "Custom market coverage",
      "14-day+ horizons",
      "Unlimited API access",
      "Bulk data exports",
      "Model transparency reports",
      "Dedicated account manager",
      "SLA guarantees",
    ],
    cta: "Contact Us",
    highlighted: false,
  },
];

const STATS = [
  { value: "< 5%", label: "Mean Absolute Error" },
  { value: "48h+", label: "Forecast Horizon" },
  { value: "Hourly", label: "Granularity" },
  { value: "06:00", label: "Daily Delivery" },
];

export default function LandingPage({ onNavigate }) {
  return (
    <div className="landing">
      {/* Hero */}
      <section className="hero">
        <div className="hero-content">
          <h1>European Energy Price Forecasts</h1>
          <p className="hero-subtitle">
            Machine learning-powered day-ahead electricity price forecasting.
            Accurate, timely, and easy to integrate.
          </p>
          <div className="hero-actions">
            <button
              className="btn btn-primary btn-lg"
              onClick={() => onNavigate("signup")}
            >
              Get Started Free
            </button>
            <button
              className="btn btn-outline btn-lg"
              onClick={() => {
                document
                  .getElementById("demo-section")
                  ?.scrollIntoView({ behavior: "smooth" });
              }}
            >
              See Live Demo
            </button>
          </div>
          <div className="hero-stats">
            {STATS.map((stat) => (
              <div key={stat.label} className="hero-stat">
                <span className="hero-stat-value">{stat.value}</span>
                <span className="hero-stat-label">{stat.label}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Live Demo Chart */}
      <section id="demo-section" className="section">
        <div className="section-container">
          <div className="section-header">
            <h2>Live Forecast Preview</h2>
            <p>
              See our model in action. This chart shows actual vs. forecasted
              prices for the German Day-Ahead market.
            </p>
          </div>
          <DemoChart />
        </div>
      </section>

      {/* How it works */}
      <section className="section section-alt">
        <div className="section-container">
          <div className="section-header">
            <h2>How It Works</h2>
            <p>From data to decision in three simple steps.</p>
          </div>
          <div className="steps-grid">
            <div className="step-card">
              <div className="step-number">1</div>
              <h3>We Collect</h3>
              <p>
                Real-time data from ENTSO-E, weather services, and commodity
                markets feeds our models continuously.
              </p>
            </div>
            <div className="step-card">
              <div className="step-number">2</div>
              <h3>We Forecast</h3>
              <p>
                Our ensemble of XGBoost and SARIMAX models generates hourly
                price forecasts with confidence intervals.
              </p>
            </div>
            <div className="step-card">
              <div className="step-number">3</div>
              <h3>You Decide</h3>
              <p>
                Access forecasts via our dashboard, daily CSV, or REST API.
                Integrate into your trading or procurement workflow.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Markets */}
      <section className="section">
        <div className="section-container">
          <div className="section-header">
            <h2>Market Coverage</h2>
            <p>
              We're starting with the most liquid European electricity markets
              and expanding.
            </p>
          </div>
          <div className="markets-grid">
            {MARKETS.map((market) => (
              <div key={market.name} className="market-card">
                <div className="market-card-header">
                  <span className="market-country">{market.country}</span>
                  <span
                    className={`market-status market-status-${market.status}`}
                  >
                    {market.status === "live" ? "Live" : "Coming Soon"}
                  </span>
                </div>
                <h3>{market.name}</h3>
                <p>{market.description}</p>
                <span className="market-type">{market.type}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section className="section section-alt" id="pricing-section">
        <div className="section-container">
          <div className="section-header">
            <h2>Simple, Transparent Pricing</h2>
            <p>Start free. Upgrade when you need more.</p>
          </div>
          <div className="pricing-grid">
            {TIERS.map((tier) => (
              <div
                key={tier.name}
                className={`pricing-card ${
                  tier.highlighted ? "pricing-card-highlighted" : ""
                }`}
              >
                {tier.highlighted && (
                  <div className="pricing-badge">Most Popular</div>
                )}
                <h3>{tier.name}</h3>
                <div className="pricing-amount">
                  <span className="pricing-price">{tier.price}</span>
                  <span className="pricing-detail">{tier.priceDetail}</span>
                </div>
                <ul className="pricing-features">
                  {tier.features.map((f) => (
                    <li key={f}>{f}</li>
                  ))}
                </ul>
                <button
                  className={`btn btn-lg ${
                    tier.highlighted ? "btn-primary" : "btn-outline"
                  }`}
                  onClick={() => onNavigate("signup")}
                >
                  {tier.cta}
                </button>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="section cta-section">
        <div className="section-container cta-container">
          <h2>Ready to forecast smarter?</h2>
          <p>
            Join energy traders and procurement teams who trust AmonHen for
            price intelligence.
          </p>
          <button
            className="btn btn-primary btn-lg"
            onClick={() => onNavigate("signup")}
          >
            Get Started Free
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer className="landing-footer">
        <div className="section-container footer-content">
          <div className="footer-brand">
            <strong>AmonHen</strong>
            <span>European Energy Price Forecasting</span>
          </div>
          <div className="footer-links">
            <button onClick={() => onNavigate("dashboard")}>Dashboard</button>
            <button
              onClick={() =>
                document
                  .getElementById("pricing-section")
                  ?.scrollIntoView({ behavior: "smooth" })
              }
            >
              Pricing
            </button>
          </div>
        </div>
      </footer>
    </div>
  );
}
