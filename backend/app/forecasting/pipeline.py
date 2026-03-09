"""End-to-end forecasting pipeline.

Orchestrates the full workflow:
1. Load target and feature data from the database
2. Build feature matrix (calendar, lags, fundamentals)
3. Train/load models (with proper train/validation split)
4. Generate forecasts
5. Store results
"""

import json
import logging
from datetime import datetime

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.forecasting.features.calendar import add_calendar_features
from app.forecasting.features.lags import add_lag_features, add_rolling_features
from app.forecasting.features.fundamental import build_feature_matrix
from app.forecasting.features.forward_curve import (
    add_forward_curve_features,
    add_forward_curve_forecast_features,
    get_forward_col_names,
)
from app.forecasting.models.xgboost_model import XGBoostForecastModel
from app.forecasting.models.sarimax_model import SARIMAXForecastModel
from app.forecasting.ensemble import WeightedEnsemble
from app.models import ForecastTarget, ForecastRun, ForecastResult

logger = logging.getLogger(__name__)

MODEL_REGISTRY = {
    "xgboost": XGBoostForecastModel,
    "sarimax": SARIMAXForecastModel,
}

# Hold back the last N hours for validation (7 days)
VALIDATION_HOURS = 168


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

    # Forward curve features: use last known commodity/forward prices
    fwd_cols = get_forward_col_names(forecast_part)
    if fwd_cols:
        forecast_part = add_forward_curve_forecast_features(
            forecast_part, df_train, fwd_cols,
        )

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

    Uses a train/validation split: trains on all data except the last
    VALIDATION_HOURS, evaluates on the held-out set, then reports
    out-of-sample metrics alongside in-sample metrics.

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
    forward_series_ids = config.get("forward_series_ids", [])
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

        # Step 2: Add forward curve / commodity features
        if forward_series_ids:
            df = add_forward_curve_features(
                df, db, forward_series_ids,
                pd.Timestamp(training_start), pd.Timestamp(training_end),
            )
            logger.info(
                "Forward curve features added: %s",
                get_forward_col_names(df),
            )

        # Step 3: Add engineered features
        df = add_calendar_features(df)
        df = add_lag_features(df, value_col="target")
        df = add_rolling_features(df, value_col="target")

        # Drop rows with NaN from lag/rolling features
        df = df.dropna()

        if len(df) < VALIDATION_HOURS + 100:
            run.status = "failed"
            run.metrics_json = json.dumps({
                "error": f"Not enough data after feature engineering. "
                         f"Need at least {VALIDATION_HOURS + 100} rows, got {len(df)}."
            })
            db.commit()
            return run

        # Step 4: Train/validation split
        feature_cols = [c for c in df.columns if c not in ("timestamp", "target")]

        df_train = df.iloc[:-VALIDATION_HOURS]
        df_val = df.iloc[-VALIDATION_HOURS:]

        X_train = df_train[feature_cols]
        y_train = df_train["target"]
        X_val = df_val[feature_cols]
        y_val = df_val["target"]

        logger.info(
            "Train/val split: %d train rows, %d validation rows",
            len(X_train), len(X_val),
        )

        # Step 5: Train models
        models = []
        for model_name in model_names:
            model_cls = MODEL_REGISTRY.get(model_name)
            if model_cls:
                model_params = config.get(f"{model_name}_params", {})
                models.append(model_cls(**model_params))

        if not models:
            raise ValueError(f"No valid models found in config: {model_names}")

        all_metrics = {}

        if len(models) == 1:
            model = models[0]
            train_metrics = model.train(X_train, y_train)

            # Out-of-sample validation metrics
            val_preds = model.predict(X_val)
            val_metrics = model.compute_metrics(y_val, val_preds)

            all_metrics = {
                "train": train_metrics,
                "validation": val_metrics,
            }
            logger.info("Train MAE: %.2f, Val MAE: %.2f",
                        train_metrics["mae"], val_metrics["mae"])
        else:
            ensemble = WeightedEnsemble(models, weights=ensemble_weights)
            model_train_metrics = ensemble.train_all(X_train, y_train)

            # Optimize ensemble weights on validation data
            ensemble.optimize_weights(X_val, y_val)

            val_preds = ensemble.predict(X_val)
            val_metrics = models[0].compute_metrics(y_val, val_preds)

            all_metrics = {
                "models": model_train_metrics,
                "ensemble_weights": ensemble.weights,
                "validation": val_metrics,
            }

        # Now retrain on full data for the actual forecast
        X_full = df[feature_cols]
        y_full = df["target"]

        if len(models) == 1:
            model.train(X_full, y_full)
        else:
            ensemble.train_all(X_full, y_full)

        run.metrics_json = json.dumps(all_metrics)

        # Step 6: Generate forecast
        horizon_hours = target.horizon_hours or 24
        last_timestamp = pd.Timestamp(df["timestamp"].iloc[-1])

        X_forecast, future_timestamps = _build_forecast_features(
            df, feature_cols, horizon_hours, last_timestamp,
        )

        if len(models) == 1:
            preds, lower, upper = model.predict_intervals(X_forecast)
        else:
            preds, lower, upper = ensemble.predict_intervals(X_forecast)

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
        logger.exception("Forecast run %d failed", run.id)
        run.status = "failed"
        run.metrics_json = json.dumps({"error": str(e)})
        db.commit()

    return run
