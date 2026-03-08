"""End-to-end forecasting pipeline.

Orchestrates the full workflow:
1. Load target and feature data from the database
2. Build feature matrix (calendar, lags, fundamentals)
3. Train/load models
4. Generate forecasts
5. Store results
"""

import json
from datetime import datetime

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.forecasting.features.calendar import add_calendar_features
from app.forecasting.features.lags import add_lag_features, add_rolling_features
from app.forecasting.features.fundamental import build_feature_matrix
from app.forecasting.models.xgboost_model import XGBoostForecastModel
from app.forecasting.models.sarimax_model import SARIMAXForecastModel
from app.forecasting.ensemble import WeightedEnsemble
from app.models import ForecastTarget, ForecastRun, ForecastResult


MODEL_REGISTRY = {
    "xgboost": XGBoostForecastModel,
    "sarimax": SARIMAXForecastModel,
}


def _build_forecast_features(
    df_train: pd.DataFrame,
    feature_cols: list[str],
    horizon_hours: int,
    last_timestamp: pd.Timestamp,
) -> tuple[pd.DataFrame, pd.DatetimeIndex]:
    """Build feature matrix for the forecast horizon.

    Calendar features are computed exactly. Lag/rolling features are
    derived from the training tail. Fundamental features (load, weather)
    are forward-filled from last known values.
    """
    future_timestamps = pd.date_range(
        start=last_timestamp + pd.Timedelta(hours=1),
        periods=horizon_hours,
        freq="h",
    )

    # Build future rows with calendar features
    forecast_rows = []
    for ts in future_timestamps:
        forecast_rows.append({
            "timestamp": ts,
            "target": np.nan,
            "hour": ts.hour,
            "day_of_week": ts.dayofweek,
            "month": ts.month,
            "is_weekend": 1 if ts.dayofweek >= 5 else 0,
            "quarter": ts.quarter,
            "week_of_year": ts.isocalendar()[1],
        })
    forecast_df = pd.DataFrame(forecast_rows)

    # Combine tail of training data with forecast rows for lag computation
    tail_size = 168 + 1  # max lag (1 week) + buffer
    tail = df_train.tail(tail_size).copy()
    combined = pd.concat([tail, forecast_df], ignore_index=True)
    combined = add_lag_features(combined, value_col="target")
    combined = add_rolling_features(combined, value_col="target")

    # Extract forecast portion
    forecast_part = combined.tail(horizon_hours).copy()

    # Forward-fill fundamental features from last known values
    for col in feature_cols:
        if col not in forecast_part.columns:
            last_val = df_train[col].iloc[-1] if col in df_train.columns else 0.0
            forecast_part[col] = last_val

    forecast_part = forecast_part.ffill().fillna(0)

    # Ensure we return exactly the columns the model expects
    for col in feature_cols:
        if col not in forecast_part.columns:
            forecast_part[col] = 0.0

    return forecast_part[feature_cols].reset_index(drop=True), future_timestamps


def run_forecast(
    db: Session,
    target_id: int,
    forecast_start: datetime,
    training_start: datetime | None = None,
) -> ForecastRun:
    """Execute a full forecasting pipeline for a given target.

    Args:
        db: Database session.
        target_id: ID of the forecast target.
        forecast_start: Start time of the forecast period.
        training_start: Start time of training data. If None, uses all available data.

    Returns:
        ForecastRun record with results.
    """
    target = db.query(ForecastTarget).filter(ForecastTarget.id == target_id).first()
    if not target:
        raise ValueError(f"Forecast target {target_id} not found")

    # Parse model config
    config = json.loads(target.model_config_json) if target.model_config_json else {}
    model_names = config.get("models", ["xgboost"])
    feature_series_ids = config.get("feature_series_ids", [])
    ensemble_weights = config.get("ensemble_weights", None)

    # Create forecast run record
    run = ForecastRun(
        forecast_target_id=target_id,
        run_timestamp=datetime.utcnow(),
        status="running",
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    try:
        # Step 1: Build feature matrix from database
        training_end = forecast_start
        if training_start is None:
            training_start = pd.Timestamp("2020-01-01")

        target_series_id = config.get("target_series_id", 1)

        df = build_feature_matrix(
            db, target_series_id, feature_series_ids,
            pd.Timestamp(training_start), pd.Timestamp(training_end),
        )

        if df.empty:
            run.status = "failed"
            run.metrics_json = json.dumps({"error": "No training data available"})
            db.commit()
            return run

        # Step 2: Add engineered features
        df = add_calendar_features(df)
        df = add_lag_features(df, value_col="target")
        df = add_rolling_features(df, value_col="target")

        # Drop rows with NaN from lag/rolling features
        df = df.dropna()

        if df.empty:
            run.status = "failed"
            run.metrics_json = json.dumps({"error": "Not enough data after feature engineering"})
            db.commit()
            return run

        # Step 3: Split features and target
        feature_cols = [c for c in df.columns if c not in ("timestamp", "target")]
        X_train = df[feature_cols]
        y_train = df["target"]

        # Step 4: Train models
        models = []
        for model_name in model_names:
            model_cls = MODEL_REGISTRY.get(model_name)
            if model_cls:
                model_params = config.get(f"{model_name}_params", {})
                models.append(model_cls(**model_params))

        if not models:
            raise ValueError(f"No valid models found in config: {model_names}")

        if len(models) == 1:
            model = models[0]
            metrics = model.train(X_train, y_train)
            run.metrics_json = json.dumps(metrics)
        else:
            ensemble = WeightedEnsemble(models, weights=ensemble_weights)
            all_metrics = ensemble.train_all(X_train, y_train)
            run.metrics_json = json.dumps({"models": all_metrics})

        # Step 5: Generate forecast
        horizon_hours = target.horizon_hours or 24
        last_timestamp = pd.Timestamp(df["timestamp"].iloc[-1])

        X_forecast, future_timestamps = _build_forecast_features(
            df, feature_cols, horizon_hours, last_timestamp,
        )

        if len(models) == 1:
            preds, lower, upper = model.predict_intervals(X_forecast)
        else:
            preds = ensemble.predict(X_forecast)
            lower = preds
            upper = preds

        # Store forecast results
        for i, ts in enumerate(future_timestamps):
            db.add(ForecastResult(
                forecast_run_id=run.id,
                timestamp=ts.to_pydatetime(),
                value=float(preds[i]),
                lower_bound=float(lower[i]) if lower is not None else None,
                upper_bound=float(upper[i]) if upper is not None else None,
            ))

        run.status = "completed"
        db.commit()

    except Exception as e:
        run.status = "failed"
        run.metrics_json = json.dumps({"error": str(e)})
        db.commit()

    return run
