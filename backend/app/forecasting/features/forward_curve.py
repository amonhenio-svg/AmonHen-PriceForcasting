"""Forward curve feature engineering for spread-based price forecasting.

Instead of predicting the absolute day-ahead price, this module enables a
"spread" approach: the model predicts the deviation between the spot price
and a baseline implied by longer-term forward/futures prices.

Benefits:
- The forward curve already embeds market consensus on fundamentals
  (fuel costs, carbon, expected demand, policy, etc.)
- The model only needs to learn *short-term deviations* (weather surprises,
  outages, demand spikes, renewable intermittency)
- More stable predictions — large systematic shifts are captured by the
  forward curve, not the ML model

If power forward curves (EEX baseload) are not available, commodity
fuel costs are used as proxy features: the model learns the fuel-to-power
spread implicitly.
"""

import logging

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.models import SeriesDefinition, TimeSeriesData

logger = logging.getLogger(__name__)


def add_forward_curve_features(
    df: pd.DataFrame,
    db: Session,
    forward_series_ids: list[int],
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> pd.DataFrame:
    """Add forward curve / commodity price features to the feature matrix.

    For each forward series:
    1. Fetches daily data from DB (already stored hourly via ffill in ingestion)
    2. Left-joins on timestamp
    3. If a "baseload" series exists, also computes the spot-forward spread
       as an explicit feature

    Args:
        df: Feature matrix with 'timestamp' and 'target' columns.
        db: Database session.
        forward_series_ids: IDs of forward curve / commodity SeriesDefinitions.
        start: Start of the time range.
        end: End of the time range.

    Returns:
        DataFrame with forward curve columns added.
    """
    if not forward_series_ids:
        return df

    df = df.copy()

    for series_id in forward_series_ids:
        series_def = db.query(SeriesDefinition).filter(
            SeriesDefinition.id == series_id
        ).first()
        if not series_def:
            logger.warning("Forward curve series id=%d not found, skipping", series_id)
            continue

        # Fetch series data
        records = (
            db.query(TimeSeriesData.timestamp, TimeSeriesData.value)
            .filter(
                TimeSeriesData.series_id == series_id,
                TimeSeriesData.timestamp >= start,
                TimeSeriesData.timestamp <= end,
            )
            .order_by(TimeSeriesData.timestamp)
            .all()
        )

        if not records:
            logger.warning(
                "No data for forward series '%s' (id=%d), skipping",
                series_def.name, series_id,
            )
            continue

        fwd_df = pd.DataFrame(records, columns=["timestamp", "value"])
        col_name = _series_col_name(series_def.name)
        fwd_df = fwd_df.rename(columns={"value": col_name})

        df = df.merge(fwd_df, on="timestamp", how="left")
        # Forward-fill commodity prices (they're daily, market may be closed)
        df[col_name] = df[col_name].ffill()

        logger.info(
            "Added forward feature '%s' (%d non-null values)",
            col_name, df[col_name].notna().sum(),
        )

        # If this is a baseload power forward, compute the spot-forward spread
        if "baseload" in series_def.name.lower() and "target" in df.columns:
            spread_col = f"spread_vs_{col_name}"
            df[spread_col] = df["target"] - df[col_name]
            logger.info("Added spread feature '%s'", spread_col)

    return df


def add_forward_curve_forecast_features(
    forecast_df: pd.DataFrame,
    df_train: pd.DataFrame,
    forward_col_names: list[str],
) -> pd.DataFrame:
    """Add forward curve features to the forecast horizon DataFrame.

    For the forecast period, forward curve values are:
    1. Looked up if data exists for those future timestamps
    2. Otherwise forward-filled from the last known training value

    This is appropriate because commodity/forward prices are slow-moving
    relative to hourly spot prices.

    Args:
        forecast_df: DataFrame for the forecast horizon.
        df_train: Full training DataFrame (to get last known values).
        forward_col_names: Column names of forward features.

    Returns:
        forecast_df with forward columns populated.
    """
    forecast_df = forecast_df.copy()

    for col in forward_col_names:
        if col not in forecast_df.columns:
            if col in df_train.columns:
                last_val = df_train[col].iloc[-1]
                if pd.isna(last_val):
                    # Walk back to find last non-null
                    valid = df_train[col].dropna()
                    last_val = valid.iloc[-1] if len(valid) > 0 else 0.0
                forecast_df[col] = last_val
            else:
                forecast_df[col] = 0.0

    return forecast_df


def get_forward_col_names(df: pd.DataFrame) -> list[str]:
    """Identify forward curve / commodity columns in a DataFrame.

    Convention: forward curve columns are prefixed with commodity series
    names or contain 'forward', 'futures', 'baseload', 'commodity'.
    """
    commodity_indicators = [
        "ttf_gas", "brent", "coal", "api2", "carbon", "eua",
        "henry_hub", "natural_gas",
        "baseload", "peakload", "forward", "futures",
        "spread_vs_",
    ]
    return [
        col for col in df.columns
        if any(ind in col.lower() for ind in commodity_indicators)
    ]


def _series_col_name(name: str) -> str:
    """Convert a series name to a DataFrame column name."""
    return name.replace(" ", "_").lower()
