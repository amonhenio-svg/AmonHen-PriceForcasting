import React, { useEffect, useState } from "react";
import { getForecastTargets, getForecastRuns } from "../services/api";

export default function ForecastPanel({ market, onSelectRun, selectedRunId }) {
  const [targets, setTargets] = useState([]);
  const [runs, setRuns] = useState([]);
  const [selectedTarget, setSelectedTarget] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!market) {
      setTargets([]);
      setRuns([]);
      setSelectedTarget(null);
      return;
    }
    getForecastTargets(market.id)
      .then((t) => {
        setTargets(t);
        if (t.length > 0) setSelectedTarget(t[0]);
      })
      .catch((err) => setError(err.message));
  }, [market]);

  useEffect(() => {
    if (!selectedTarget) {
      setRuns([]);
      return;
    }
    getForecastRuns(selectedTarget.id)
      .then(setRuns)
      .catch(() => setRuns([]));
  }, [selectedTarget]);

  if (!market) return null;

  return (
    <div className="forecast-panel">
      <h3>Forecasts</h3>
      {error && <p className="error">{error}</p>}
      {targets.length === 0 ? (
        <p className="muted">No forecast targets configured for this market.</p>
      ) : (
        <>
          <div className="target-selector">
            {targets.map((t) => (
              <button
                key={t.id}
                className={`target-btn ${t.id === selectedTarget?.id ? "active" : ""}`}
                onClick={() => {
                  setSelectedTarget(t);
                  onSelectRun(null);
                }}
              >
                {t.name}
                <span className="target-horizon">{t.horizon_hours}h</span>
              </button>
            ))}
          </div>
          {runs.length > 0 && (
            <div className="run-list">
              <h4>Recent Runs</h4>
              <ul>
                {runs.slice(0, 5).map((run) => (
                  <li
                    key={run.id}
                    className={run.id === selectedRunId ? "selected" : ""}
                    onClick={() => onSelectRun(run.id)}
                  >
                    <span className={`status status-${run.status}`}>
                      {run.status}
                    </span>
                    <span className="run-time">
                      {new Date(run.run_timestamp).toLocaleString()}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}
    </div>
  );
}
