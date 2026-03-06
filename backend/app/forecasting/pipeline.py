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

        # Get target series ID from the market's price series
        # TODO: resolve target_series_id from market configuration
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
            # Single model
            model = models[0]
            metrics = model.train(X_train, y_train)
            run.metrics_json = json.dumps(metrics)
        else:
            # Ensemble
            ensemble = WeightedEnsemble(models, weights=ensemble_weights)
            all_metrics = ensemble.train_all(X_train, y_train)
            run.metrics_json = json.dumps({"models": all_metrics})

        # Step 5: Generate forecast
        # TODO: Build feature matrix for forecast period
        # This requires feature forecasts (weather, load, etc.)

        run.status = "completed"
        db.commit()

    except Exception as e:
        run.status = "failed"
        run.metrics_json = json.dumps({"error": str(e)})
        db.commit()

    return run
