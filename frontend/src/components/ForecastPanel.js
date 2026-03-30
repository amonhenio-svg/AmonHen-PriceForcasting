import React, { useEffect, useState, useCallback } from "react";
import {
  getForecastTargets,
  getForecastRuns,
  runForecast,
  getForecastAccuracy,
} from "../services/api";

function MetricsBadge({ label, value, unit }) {
  if (value == null) return null;
  return (
    <div className="metric-badge">
      <span className="metric-label">{label}</span>
      <span className="metric-value">
        {typeof value === "number" ? value.toFixed(2) : value}
        {unit && <span className="metric-unit">{unit}</span>}
      </span>
    </div>
  );
}

function RunMetrics({ run }) {
  if (!run || !run.metrics_json) return null;

  let metrics;
  try {
    metrics = JSON.parse(run.metrics_json);
  } catch {
    return null;
  }

  if (metrics.error) {
    return <p className="error" style={{ fontSize: "0.8rem" }}>{metrics.error}</p>;
  }

  const val = metrics.validation || {};
  const train = metrics.train || {};

  return (
    <div className="run-metrics">
      <h5>Model Performance</h5>
      <div className="metrics-row">
        {val.mae != null && <MetricsBadge label="Val MAE" value={val.mae} unit="EUR" />}
        {val.rmse != null && <MetricsBadge label="Val RMSE" value={val.rmse} unit="EUR" />}
        {val.mape != null && <MetricsBadge label="Val MAPE" value={val.mape} unit="%" />}
        {train.mae != null && <MetricsBadge label="Train MAE" value={train.mae} unit="EUR" />}
      </div>
    </div>
  );
}

function AccuracyPanel({ runId }) {
  const [accuracy, setAccuracy] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!runId) {
      setAccuracy(null);
      return;
    }
    setLoading(true);
    getForecastAccuracy(runId)
      .then(setAccuracy)
      .catch(() => setAccuracy(null))
      .finally(() => setLoading(false));
  }, [runId]);

  if (!runId) return null;
  if (loading) return <p className="muted" style={{ fontSize: "0.8rem" }}>Checking accuracy...</p>;
  if (!accuracy || accuracy.points.length === 0) {
    return <p className="muted" style={{ fontSize: "0.8rem" }}>No actuals yet to compare against.</p>;
  }

  return (
    <div className="accuracy-panel">
      <h5>Forecast vs Actual</h5>
      <div className="metrics-row">
        <MetricsBadge label="MAE" value={accuracy.mae} unit="EUR" />
        <MetricsBadge label="RMSE" value={accuracy.rmse} unit="EUR" />
        <MetricsBadge label="MAPE" value={accuracy.mape} unit="%" />
      </div>
      <p className="muted" style={{ fontSize: "0.75rem", marginTop: "0.25rem" }}>
        Based on {accuracy.points.length} hours with actuals available
      </p>
    </div>
  );
}

export default function ForecastPanel({ market, onSelectRun, selectedRunId, onTargetChange }) {
  const [targets, setTargets] = useState([]);
  const [runs, setRuns] = useState([]);
  const [selectedTarget, setSelectedTarget] = useState(null);
  const [error, setError] = useState(null);
  const [running, setRunning] = useState(false);

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
        if (t.length > 0) {
          setSelectedTarget(t[0]);
          if (onTargetChange) onTargetChange(t[0]);
        }
      })
      .catch((err) => setError(err.message));
  }, [market]);

  const loadRuns = useCallback(() => {
    if (!selectedTarget) {
      setRuns([]);
      return;
    }
    getForecastRuns(selectedTarget.id)
      .then((runs) => {
        setRuns(runs);
        // Auto-select the latest completed run if none is selected
        if (!selectedRunId && runs.length > 0) {
          const completed = runs.find((r) => r.status === "completed");
          if (completed) onSelectRun(completed.id);
        }
      })
      .catch(() => setRuns([]));
  }, [selectedTarget, selectedRunId, onSelectRun]);

  useEffect(() => {
    loadRuns();
  }, [loadRuns]);

  // Auto-refresh runs every 30 seconds
  useEffect(() => {
    if (!selectedTarget) return;
    const interval = setInterval(loadRuns, 30000);
    return () => clearInterval(interval);
  }, [selectedTarget, loadRuns]);

  const handleRunForecast = async () => {
    if (!selectedTarget) return;
    setRunning(true);
    setError(null);
    try {
      const run = await runForecast(selectedTarget.id);
      loadRuns();
      onSelectRun(run.id);
    } catch (err) {
      setError(err.message);
    } finally {
      setRunning(false);
    }
  };

  if (!market) return null;

  // Find selected run object for metrics display
  const selectedRun = runs.find((r) => r.id === selectedRunId);

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
                  if (onTargetChange) onTargetChange(t);
                }}
              >
                {t.name}
                <span className="target-horizon">{t.horizon_hours}h</span>
              </button>
            ))}
          </div>

          <div className="forecast-actions">
            {selectedTarget && (
              <button
                className="run-forecast-btn"
                onClick={handleRunForecast}
                disabled={running}
              >
                {running ? "Running..." : "Run Forecast"}
              </button>
            )}
          </div>

          {/* Model metrics for selected run */}
          {selectedRun && <RunMetrics run={selectedRun} />}
          {selectedRunId && <AccuracyPanel runId={selectedRunId} />}

          {runs.length > 0 && (
            <div className="run-list">
              <h4>Recent Runs</h4>
              <ul>
                {runs.slice(0, 8).map((run) => (
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
