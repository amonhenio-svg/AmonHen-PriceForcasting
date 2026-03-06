"""Fundamental feature engineering for energy price forecasting.

Combines multiple data series into a feature matrix suitable for model training.
"""

import pandas as pd
from sqlalchemy.orm import Session

from app.models import SeriesDefinition, TimeSeriesData


def build_feature_matrix(
    db: Session,
    target_series_id: int,
    feature_series_ids: list[int],
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> pd.DataFrame:
    """Build a feature matrix by joining target and feature series.

    Creates a wide-format DataFrame where each column is a different series,
    aligned on timestamp.

    Args:
        db: Database session.
        target_series_id: ID of the target series (what we're predicting).
        feature_series_ids: IDs of feature series.
        start: Start of the time range.
        end: End of the time range.

    Returns:
        DataFrame with 'timestamp', 'target', and one column per feature series.
    """
    # Fetch target series
    target_data = _fetch_series_as_df(db, target_series_id, start, end)
    if target_data.empty:
        return pd.DataFrame()

    target_data = target_data.rename(columns={"value": "target"})

    # Fetch and join each feature series
    for series_id in feature_series_ids:
        series_def = db.query(SeriesDefinition).filter(SeriesDefinition.id == series_id).first()
        if not series_def:
            continue

        feature_data = _fetch_series_as_df(db, series_id, start, end)
        if feature_data.empty:
            continue

        col_name = series_def.name.replace(" ", "_").lower()
        feature_data = feature_data.rename(columns={"value": col_name})
        target_data = target_data.merge(feature_data, on="timestamp", how="left")

    return target_data


def _fetch_series_as_df(
    db: Session,
    series_id: int,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> pd.DataFrame:
    """Fetch a time series from the database as a DataFrame."""
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
        return pd.DataFrame(columns=["timestamp", "value"])

    return pd.DataFrame(records, columns=["timestamp", "value"])
